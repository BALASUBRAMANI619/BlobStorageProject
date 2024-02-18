from flask import Flask, render_template, redirect, request, url_for
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from datetime import datetime, timedelta
from urllib.parse import quote
import os
#from app_upload import generate_SAS
#

app = Flask(__name__)

client_id = os.environ['AZURE_CLIENT_ID']
tenant_id = os.environ['AZURE_TENANT_ID']
client_secret = os.environ['AZURE_CLIENT_SECRET']
vault_url = os.environ["AZURE_VAULT_URL"]
account_url = os.environ["AZURE_STORAGE_URL"]

account_name = account_url.split(".")[0].split("//")[1]

secret_name = "myfirstkey"

credentials = ClientSecretCredential(client_id=client_id,
                                     client_secret=client_secret,
                                     tenant_id=tenant_id)

# create a secret client object
secret_client = SecretClient(vault_url=vault_url, credential=credentials)
# retrieve the secret value from key vault
secret = secret_client.get_secret(secret_name)

blob_credentials = DefaultAzureCredential()
container_name = "fileuploadproject"

# Set client to access Azure Storage container
blob_service_client = BlobServiceClient(account_url=account_url,
                                        credential=blob_credentials)

# Get the container client
container_client = blob_service_client.get_container_client(
    container=container_name)


@app.route('/')
def index():
  blob_names = []
  blob_urls = []

  for blob_data in container_client.list_blobs():
    blob_name = blob_data.name
    blob_names.append(blob_name)
    blob_client = container_client.get_blob_client(blob_name)
    #print(f"blob_name: {blob_name}")
    blob_url = blob_client.url
    #print(f"blob_url: {blob_urls}")
    blob_urls.append(blob_url)

  return render_template("index.html",
                         blob_names=blob_names,
                         blob_urls=blob_urls)


@app.route('/upload', methods=['POST'])
def upload():

  if request.method == 'POST':
    # Access the uploaded file from the request
    uploaded_file = request.files['file']

    # Generate a unique blob name (you can modify this as needed)
    #blob_name = f"uploaded_files/{uploaded_file.filename}"

    # Generate a unique blob name without a specific folder
    blob_name = uploaded_file.filename

    # Create a BlobClient and upload the file
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(uploaded_file.stream.read(), overwrite=True)
    return redirect(url_for('index'))

  return "Hello"


@app.route('/view_blob/<blob_name>')
def view_blob(blob_name):
  blob_client = container_client.get_blob_client(blob_name)
  blob_url = blob_client.url
  properties = blob_client.get_blob_properties()

  return render_template("view_blob.html",
                         blob_name=blob_name,
                         blob_url=blob_url,
                         properties=properties)


@app.route('/delete_blob/<blob_name>')
def delete_blob(blob_name):
  blob_client = container_client.get_blob_client(blob_name)
  blob_client.delete_blob()
  return redirect(url_for('index'))


@app.route('/share_blob', methods=['POST'])
def share_blob():
  if request.method == 'POST':
    permission = request.form.get('permission')
    if permission == "read":
      blob_permissions = BlobSasPermissions(read=True)
    elif permission == "write":
      blob_permissions = BlobSasPermissions(write=True)
    elif permission == "delete":
      blob_permissions = BlobSasPermissions(delete=True)
    else:
      # Default to read-only if the selected option is not recognized
      blob_permissions = BlobSasPermissions(read=True)

    blob = request.form.get('blob_name')
    print("blob name : ", blob)

    # Get a BlobClient for the specific blob
    blob_client = blob_service_client.get_blob_client(container_name, blob)
    sas_token = generate_SAS(blob, blob_permissions)
    print("permission value  ib share_blob route: ", blob_permissions)
    #print("SAS Token : ", sas_token)
    # Construct the complete URL with the SAS token
    blob_url_with_sas = f"{blob_client.url}?{sas_token}"
    print("blob_url_with_sas : ", blob_url_with_sas)
    return render_template("share_blob.html", sharelink=blob_url_with_sas)

  return render_template("share_blob.html", sharelink=None)


def generate_SAS(blob, blob_permissions):
  #start_time = datetime.now()
  #expiry_time = start_time + timedelta(days=7)
  print("permisson value : ", blob_permissions)
  print(f"data type of acccess_level is {type(blob_permissions)}")
  expiration = datetime.utcnow() + timedelta(hours=1)
  print("expiry time : ", expiration)
  print(f"data type of expiry_time is {type(expiration)}")
  # Convert expiry_time to ISO format string
  expiry_time_str = expiration.isoformat()

  key_info = blob_service_client.get_user_delegation_key(
      datetime.utcnow(), expiration)

  SAS_Token = generate_blob_sas(
      account_name=account_name,
      container_name=container_name,
      blob_name=blob,
      account_key=None,  # Set account_key to None when using Managed Identity
      user_delegation_key=
      key_info,  # Use the user delegation key from BlobServiceClient
      permission=blob_permissions,
      expiry=expiry_time_str)
  # URL encode the SAS token
  encoded_sas_token = quote(SAS_Token)
  return encoded_sas_token


if __name__ == "__main__":
  app.run(host="0.0.0.0")
