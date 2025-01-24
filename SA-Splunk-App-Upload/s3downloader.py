New function:
 
def download_folder_from_s3(bucket_name, folder_key, local_directory, access_key, secret_key, endpoint, keep_foldername=False):
    session = boto3.session.Session()
    s3 = session.client(
        service_name='s3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint,
    )
   
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)
   
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=folder_key, MaxKeys=1000)
 
    #objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_key)
    icount = 0
    for page in pages:
        print("{} Objects processed, turning to new page".format(icount))
        for obj in page.get('Contents',[]):
            icount+=1
            #if obj['Size'] > 0:
            key = obj['Key']
            filename = key
            if not keep_foldername:
                folder_length = len(folder_key if folder_key[-1]=="/" else folder_key + "/")
                if key[0:folder_length] == folder_key if folder_key[-1]=="/" else folder_key + "/":
                    filename = key[folder_length:]
            #local_file_path = os.path.join(local_directory, os.path.basename(key))
            local_file_path = os.path.join(local_directory,os.path.dirname(filename))
            os.makedirs(local_file_path, exist_ok=True)
            local_file_location = os.path.join(local_directory, filename)
            print(icount,"\t",local_file_location,"\t",obj['Size'])
            s3.download_file(bucket_name, key, local_file_location)
