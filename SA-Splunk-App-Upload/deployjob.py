delay = 10
retry = 3

successful = True
job_id = str(uuid.uuid4())

pyfile = os.path.join(os.getcwd(),__file__)
parent_folder = os.path.dirname(os.path.dirname(pyfile))

cluster_master_folder = os.path.join(parent_folder,"CM")
search_head_folder = os.path.join(parent_folder,"SH")
indexer_folder = os.path.join(parent_folder,"IDX")
temp_folder = os.path.join(parent_folder,"temp")

def get_file_hash(filename):
    sha256_hash = hashlib.sha256()
    with open(filename,"rb") as f:
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_filename(item):
    return item["filename"]

def get_folder_hash(folder, exclusion=["appdeploy.conf"]):
    if folder[-1] != "/":
        target_folder = folder + "/"
    else:
        target_folder = folder
    res = []
    for (dir_path, dir_names, file_names) in os.walk(target_folder):
        file_names = [{"filename": os.path.join(dir_path, i)[len(target_folder):],
                       "sha256": get_file_hash(os.path.join(dir_path, i))}
                      for i in file_names if i[0] != "." and i not in exclusion]
        res.extend(file_names)
    finalsha256 = hashlib.sha256(json.dumps(sorted(res, key=get_filename)).encode('utf-8')).hexdigest()
    send_event_hec("calculated folder hash of {} is {}".format(folder, finalsha256))
    return finalsha256

def load_deployment(config_file):
    results = {}
    try:
        config = configparser.ConfigParser()
        if os.path.exists(config_file) and os.path.isfile(config_file):
            config.read(config_file)
            for i in config:
                if i not in results:
                    results[i.lower()]={}
                for j in config[i]:
                    results[i.lower()][j.lower()] = config[i][j]
    except Exception as err:
        #send log
        results = {'default':'false'}
    send_event_hec({**results,**{"activity":"loaded deployment configuration"}})
    return results

def get_setting(results,role,app_name):
    if "default" in results:
        default_value = results["default"]["deploy"].lower() if "deploy" in results["default"] else "false"
    else:
        default_value = "false"
    if role.lower() in results:
        result_value = results[role.lower()][app_name.lower()+".deploy"] if app_name.lower()+".deploy" in results[role.lower()] else default_value
    else:
        result_value = default_value
    return result_value.lower()

def update_appdeploy_config(app_folder,app_hash):
    app_name = [i for i in app_folder.split("/") if i.strip() != ""][-1]

    config = configparser.ConfigParser()

    default_folder = os.path.join(app_folder,"default")
    config_file = os.path.join(default_folder,"appdeploy.conf")
    if not os.path.exists(default_folder):
        os.makedirs(default_folder,exist_ok=True)

    skip_deployment = "false"

    if os.path.exists(config_file):
        config.read(config_file)
        if config.has_section(app_name):
            skip_deployment = config[app_name].get("skip_deployment","false")
            config[app_name]["app_checksum"] = app_hash
            config[app_name]["app_updated_on"] = str(time.time())
        else:
            config[app_name] = {}
            config[app_name]["skip_deployment"] = skip_deployment
            config[app_name]["app_checksum"] = app_hash
            config[app_name]["app_updated_on"] = str(time.time())
        with open(config_file, 'w') as configfile:
            config.write(configfile)
    else:
        config.add_section(app_name)
        config[app_name] = {}
        config[app_name]["skip_deployment"] = skip_deployment
        config[app_name]["app_checksum"] = app_hash
        config[app_name]["app_updated_on"] = str(time.time())
        with open(config_file, 'w') as configfile:
            config.write(configfile)
    if skip_deployment == "1":
        skip_deployment = "true"
    elif skip_deployment == "0":
        skip_deployment = "false"
    else:
        skip_deployment = skip_deployment.lower().strip()
    return skip_deployment

def get_app_checksum(endpoint, account, app_name):
    url = "{}/servicesNS/-/{}/configs/conf-appdeploy/{}".format(endpoint,app_name,app_name)
    params = {"output_mode": "json"}
    headers = {"Content-Type": "application/json"}
    response = requests.get(url, auth=account, verify=False, headers=headers, params=params)
    if response.status_code == 200:
        server_sha256 = response.json()["entry"][0]["content"]["app_checksum"]
    else:
        server_sha256 = 0
    return server_sha256

def package_app(app_folder, target_folder):
    send_event_hec("packaging application {} to {}".format(app_folder, target_folder))
    app_name = [i for i in app_folder.split("/") if i.strip() != ""][-1]
    if not os.path.exists(target_folder):
        os.makedirs(target_folder, exist_ok=True)
    target_file = os.path.join(target_folder,app_name + ".spl")
    source_dir = app_folder.rstrip("/")
    with tarfile.open(target_file, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))
    send_event_hec("packaged application {} to {}".format(app_folder, target_file))
    return target_file

def install_app(endpoint, account, app_package):
    send_event_hec("installing application {} to {}".format(app_package, endpoint))
    url = "{}/services/apps/local".format(endpoint)
    with open(app_package, 'rb') as f:
        app_data = f.read()
    headers = {
        "Content-Type": "application/x-tar",
        "Content-Disposition": f"filename={os.path.basename(app_package)}",
    }
    params = { "output_mode": "json" }
    response = requests.post(url, auth=account, data=app_data, headers=headers, params=params, verify=False, timeout=3000)
    if response.status_code == 200 or response.status_code == 201:
        send_event_hec("install application {} to {}: successful".format(app_package, endpoint))
        return "successful"
    else:
        send_event_hec("install application {} to {}: {}".format(app_package, endpoint, "failed with code {}: {}".format(response.status_code, response.text)))
        return "failed with code {}: {}".format(response.status_code, response.text)

def backup_app(endpoint, account, app_name):
    send_event_hec("backing up application {} on {}".format(app_name, endpoint))
    url = "{}/services/apps/local/{}/package".format(endpoint,app_name)
    params = { "output_mode": "json" }
    response = requests.post(url, auth=account, headers={"Content-Type": "application/json"}, params=params, verify=False, timeout=3000)
    if response.status_code == 200 or response.status_code == 201:
        send_event_hec("backup application {}: successful to {} on {}".format(app_name, response.json()["entry"][0]["content"]["path"],endpoint))
        return "successful"
    else:
        send_event_hec("backup application {} on {}: {}".format(app_name, endpoint, "failed with code {}: {}".format(response.status_code, response.text)))
        return "backup failed with code {}: {}".format(response.status_code, response.text)

def remove_app(endpoint, account, app_name):
    send_event_hec("deleting application {} on {}".format(app_name, endpoint))
    url = "{}/services/apps/local/{}".format(endpoint,app_name)
    params = { "output_mode": "json" }
    response = requests.delete(url, auth=account, headers={"Content-Type": "application/json"}, params=params, verify=False, timeout=3000)
    if response.status_code == 200 or response.status_code == 201:
        send_event_hec("deleted application {}: successful on {}".format(app_name, endpoint))
        return "successful"
    else:
        send_event_hec("deletion application {} on {}: {}".format(app_name, endpoint, "failed with code {}: {}".format(response.status_code, response.text)))
        return "application deletion failed with code {}: {}".format(response.status_code, response.text)

def install_apps_to_server(app_folder,endpoint,account,package_folder,deployment_settings={'default':'false'},role='sh'):
    send_event_hec("installing applications under " + app_folder + " to " + endpoint)
    install_apps = [f.path for f in os.scandir(app_folder) if f.is_dir()]
    results = []
    for current_app in install_apps:
        app_name = [i for i in current_app.split("/") if i.strip() != ""][-1]
        local_app_hash = get_folder_hash(current_app)
        app_hash = get_app_checksum(endpoint, account, app_name)
        skip_deployment = update_appdeploy_config(current_app, local_app_hash).lower().strip()
        deploy = get_setting(deployment_settings, role, app_name)
        send_event_hec({"application":current_app,"deploy":deploy,"skip_deployment":skip_deployment,"server_hash":app_hash,"local_hash":local_app_hash})
        if skip_deployment=="false" and local_app_hash != app_hash and deploy=="true":
            backup_result="unknown"
            remove_result="unknown"
            package_file = package_app(current_app, package_folder)
            if app_hash != 0:
                backup_result = backup_app(endpoint, account, app_name)
                if backup_result == "successful":
                    remove_result = remove_app(endpoint, account, app_name)
                    if remove_result == "successful":
                        install_result = install_app(endpoint, account, package_file)
            else:
                install_result = install_app(endpoint, account, package_file)
            r = {
                "looping_folder":app_folder,
                "app_file":package_file,
                "install_result":install_result,
                "backup_result": backup_result,
                "remove_result": remove_result,
                "server_hash":app_hash,
                "local_hash":local_app_hash
            }
            send_event_hec(r)
            results.append(r)
        else:
            send_event_hec({"app_name":app_name,
                            "deploy":deploy,
                            "skip_deployment":skip_deployment,
                            "server_hash":app_hash,
                            "local_hash":local_app_hash})
    return results

def get_cm_status(endpoint,account):
    send_event_hec("retrieving indexer cluster manager status from {}".format(endpoint))
    url = "{}/services/cluster/manager/status".format(endpoint)
    params = {"output_mode": "json"}
    response = requests.get(url, auth=account, verify=False, headers={"Content-Type": "application/json"},params=params)
    if response.status_code == 200:
        status = response.json()["entry"][0]["content"]
        cm_status = not (status["maintenance_mode"] or status["rolling_restart_flag"] or status[
            "rolling_restart_or_upgrade"]) and status["service_ready_flag"] and (set([status["peers"][i]["status"] for i in status["peers"].keys()])=={"Up"})
    else:
        cm_status = False
    send_event_hec("retrieved indexer cluster manager status is {}".format(cm_status))
    return cm_status

def get_peer_bundle_status(endpoint,account):
    send_event_hec("retrieving indexer cluster peer status from {}".format(endpoint))
    url = "{}/services/cluster/manager/info".format(endpoint)
    params = {"output_mode": "json"}
    response = requests.get(url, auth=account, verify=False, headers={"Content-Type": "application/json"},params=params)
    if response.status_code == 200:
        info = response.json()["entry"][0]["content"]
        if info["last_validated_bundle"]["checksum"] == info["active_bundle"]["checksum"]:
            peer_status = "no bundle to push"
        elif info["last_validated_bundle"]["is_valid_bundle"]:
            peer_status = "successful"
        else:
            peer_status = "failed"
    else:
        peer_status = "failed with code {}: {}".format(response.status_code, response.text)
    send_event_hec("retrieved indexer cluster peer status is {}".format(peer_status))
    return peer_status

def get_indexer_endpoints(endpoint,account):
    url = "{}/services/cluster/manager/peers".format(endpoint)
    params = {"output_mode": "json"}
    response = requests.get(url, auth=account, verify=False, headers={"Content-Type": "application/json"},params=params)
    if response.status_code == 200:
        status = response.json()["entry"]
        indexer_endpoints = [i["content"]["register_search_address"] for i in status]
    else:
        indexer_endpoints = []
    send_event_hec("retrieved indexer nodes are {}".format(indexer_endpoints))
    return indexer_endpoints

def validate_bundle(endpoint,account):
    send_event_hec("validating bundle on {}".format(endpoint))
    url = "{}/services/cluster/manager/control/default/validate_bundle".format(endpoint)
    params = {"output_mode": "json"}
    response = requests.post(url, auth=account, verify=False, headers={"Content-Type": "application/json"},params=params)
    if response.status_code == 200 or response.status_code == 201:
        send_event_hec("validate bundle on {}: successful".format(endpoint))
        return "successful"
    else:
        send_event_hec("validate bundle on {}: {}".format(endpoint, "failed with code {}: {}".format(response.status_code, response.text)))
        return "failed with code {}: {}".format(response.status_code, response.text)


def restart_splunk_service(endpoint,account):
    send_event_hec("restarting service on {}".format(endpoint))
    url = "{}/services/server/control/restart".format(endpoint)
    params = {"output_mode": "json"}
    response = requests.post(url, auth=account, verify=False, headers={"Content-Type": "application/json"},params=params)
    if response.status_code == 200:
        send_event_hec("restart service on {}: successful".format(endpoint))
        return "successful"
    else:
        send_event_hec("restarting service on {}: {}".format(endpoint, "failed with code {}: {}".format(response.status_code, response.text)))
        return "failed with code {}: {}".format(response.status_code, response.text)

def apply_bundle(endpoint,account):
    send_event_hec("applying bundle on {}".format(endpoint))
    url = "{}/services/cluster/manager/control/default/apply".format(endpoint)
    params = {"output_mode": "json"}
    response = requests.post(url, auth=account, verify=False, headers={"Content-Type": "application/json"},params=params)
    if response.status_code == 200 or response.status_code == 201:
        send_event_hec("apply bundle on {}: successful".format(endpoint))
        return "successful"
    else:
        send_event_hec("apply bundle on {}: {}".format(endpoint, "failed with code {}: {}".format(response.status_code, response.text)))
        return "failed with code {}: {}".format(response.status_code, response.text)

def upload_indexer_app(endpoint, account, app_package, target_folder="master-apps"):
    send_event_hec("uploading application {} to {}".format(app_package,endpoint))
    url = "{}/services/apps/upload".format(endpoint)
    app_file = open(app_package, "rb")
    params = {
        "output_mode": "json",
        "target_folder": target_folder
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, auth=account, data=app_file.read(), verify=False, headers=headers, params=params)
    if response.status_code == 200 or response.status_code == 201:
        send_event_hec("upload application {} to {}: successful".format(app_package, endpoint))
        return "successful"
    else:
        send_event_hec("upload application {} to {}: {}".format(app_package, endpoint, "failed with code {}: {}".format(response.status_code, response.text)))
        return "failed with code {}: {}".format(response.status_code, response.text)

def upload_apps_to_cm(app_folder,endpoint,account,indexer_account,package_folder,deployment_settings={'default':'false'},role='idx'):
    send_event_hec("uploading applications under " + app_folder + " to " + endpoint)
    install_apps = [f.path for f in os.scandir(app_folder) if f.is_dir()]
    indexer_endpoints = get_indexer_endpoints(cluster_master_endpoint, cluster_master_account)
    indexer_endpoint = "https://" + indexer_endpoints[0]
    indexer_endpoint = "https://18.138.233.51:8089"
    results = []
    for current_app in install_apps:
        app_name = [i for i in current_app.split("/") if i.strip() != ""][-1]
        local_app_hash = get_folder_hash(current_app)
        app_hash = get_app_checksum(indexer_endpoint, indexer_account, app_name)
        skip_deployment = update_appdeploy_config(current_app, local_app_hash).lower().strip()
        deploy = get_setting(deployment_settings, role, app_name)
        send_event_hec({"application":current_app,"deploy":deploy,"skip_deployment":skip_deployment,"server_hash":app_hash,"local_hash":local_app_hash})
        if skip_deployment == "false" and local_app_hash != app_hash and deploy == "true":
            package_file = package_app(current_app, package_folder)
            install_result = upload_indexer_app(endpoint, account, package_file)
            r = {
                "looping_folder":app_folder,
                "app_file":package_file,
                "upload_result":install_result,
                "server_hash":app_hash,
                "local_hash":local_app_hash
            }
            send_event_hec(r)
            results.append(r)
        else:
            send_event_hec({"app_name": app_name,
                        "deploy": deploy,
                        "skip_deployment": skip_deployment,
                        "server_hash": app_hash,
                        "local_hash": local_app_hash})
    return results

def push_bundle_to_indexers(endpoint,account,delay=delay, retry=retry):
    validate_bundle(endpoint,account)
    send_event_hec("pushing applications to indexers via {}".format(endpoint))
    i = 0
    while i<retry:
        bundle_status = get_peer_bundle_status(endpoint,account)
        if bundle_status == "successful" or bundle_status[0:6] == "failed":
            i = retry + 1
        elif bundle_status == "no bundle to push":
            time.sleep(delay)
            i = i + 1
        else:
            i = retry + 1
    if bundle_status == "successful":
        time.sleep(delay)
        result=apply_bundle(endpoint,account)
        send_event_hec("pushing applications to indexers: " + result)
        return result
    else:
        return False

def send_event_hec(event,endpoint=logger_hec_endpoint,token=logger_hec_token,index=logger_hec_index, job_id=job_id,retry=retry):
    if event is None or endpoint is None or token is None or index is None \
            or event == "" or endpoint == "" or token =="" or index == "":
        return False
    if not type(event) is str:
        event = json.dumps(event)
    url = "{}/services/collector/event".format(endpoint)
    headers = {
        "Authorization": "Splunk {}".format(token)
    }
    message = {
        'time': time.time(),
        'index': index,
        'host': 'k8s_container',
        'sourcetype': 'exection:event:json',
        'source': 'python_script',
        'event': event,
        'fields': {'event_length': len(event),'job_id':job_id}
    }
    data = json.dumps(message)
    i = 0
    while i < retry:
        response = requests.post(url, headers=headers, data=data, verify=False)
        if response.status_code == 404 or response.status_code >= 500:
            i = i + 1 # service tenporarily not avaliable
        elif response.status_code == 200 or response.status_code == 201:
            i = retry + 1 # successful
        else:
            i = retry + 1 # failed
    if response.status_code in [200, 201]:
        return True
    else:
        return False

deployment_settings = load_deployment(os.path.join(parent_folder,"deploymentsettings.conf"))


"""
try:
    cm_status = get_cm_status(cluster_master_endpoint,cluster_master_account)
    peer_bundle_status = get_peer_bundle_status(cluster_master_endpoint,cluster_master_account)

    if cm_status and peer_bundle_status == "no bundle to push":
        send_event_hec("cluster master is ready to start operation")
        cm_results = install_apps_to_server(cluster_master_folder,cluster_master_endpoint,cluster_master_account,os.path.join(temp_folder,"CM"),deployment_settings,"cm")
        if (cm_results != []):
            restart_splunk_service(cluster_master_endpoint,cluster_master_account)
        sh_results = install_apps_to_server(search_head_folder,search_head_endpoint,search_head_account,os.path.join(temp_folder,"SH"),deployment_settings,"sh")
        if (sh_results != []):
            restart_splunk_service(search_head_endpoint,search_head_account)
        results = upload_apps_to_cm(indexer_folder,cluster_master_endpoint,cluster_master_account,indexer_account,os.path.join(temp_folder,"IDX"),deployment_settings,"idx")
        if results != []:
            print(push_bundle_to_indexers(cluster_master_endpoint, cluster_master_account))
    else:
        send_event_hec("cluster master is not ready")
        print("cluster master is not ready")
except Exception as err:
    send_event_hec(str(err))
    successful = False
finally:
    send_event_hec("deployment job is completed {}".format("successfully" if successful else "unsuccessfully"))

"""
