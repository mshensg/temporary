from splunk.persistconn.application import PersistentServerConnectionApplication
import json, base64, tarfile, os, io

class Upload(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_bytes):
        payload = {}
        allowed_folders = ["master-apps","manager-apps","deployment-apps","shcluster/apps"]
        status = 201
        try:
            in_string = in_bytes.decode()
            in_request = json.loads(in_string)
            method = in_request["method"] if "method" in in_request else "UNKNOWN"
            if method == "POST":
                data = base64.b64decode(in_request["payload_base64"])
                queryload = in_request["query"]
                query={i[0]:i[1] for i in queryload}
                if "target_folder" not in query:
                    target_folder = "manager-apps"
                elif query["target_folder"] in allowed_folders:
                    target_folder = query["target_folder"]
                else:
                    target_folder = "disallowed"

                payload = {
                    "target_folder": target_folder
                }
                if "debug" in query and query["debug"].lower().strip() in ["yes","true"]:
                    payload["request_data"] = in_request

                if target_folder != "disallowed":

                    target_folder = os.environ["SPLUNK_HOME"] + "/etc/" + target_folder + "/"
                    payload["extract_to"] = target_folder
                    file = io.BytesIO(data)
                    tardata = tarfile.open(fileobj=file,mode='r:gz')
                    tardata.extractall(target_folder)
                    tardata.close()
                    payload["result"] = "successful"
            else:
                payload["request_data"] = in_request
                payload["http_method"] = method
        except Exception as err:
            payload["error"] = str(err)
            status = 500
        return {'payload': payload, 'status': status}

    def handleStream(self, handle, in_bytes):
        pass

    def done(self):
        pass
