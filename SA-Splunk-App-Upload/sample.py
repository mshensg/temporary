file=".....tgz"
upload_file = open(file, "rb")
server="ip_address/fqdn"
port=8089

url = "https://{}:{}/services/apps/upload".format(server,port)
params = {
    "output_mode": "json",
    "target_folder": "master-apps",
    "debug": "false"
}
response = requests.post(url,auth=(admin_user,password),data=upload_file.read(),verify=False,headers={"Content-Type":"application/json"},params=params)
upload_file.close()
print(json.dumps(response.json(),indent=4))
