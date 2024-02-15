from flask import Flask, render_template, redirect, request, url_for, jsonify
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas, UserDelegationKey
from datetime import datetime, timedelta
from urllib.parse import quote
import os
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


@app.route("/")
def index():
  blob_name = "kkk.txt"
  try:

    # download blob data
    blob_client = container_client.get_blob_client(blob=blob_name)

    data = blob_client.download_blob().readall().decode("utf-8")

    print(f"datatype of the data is {type(data)}")

    # If the above lines executed without errors, print success message
    success_message = "Successfully connected to Azure Storage and container."
  except Exception as e:
    # If an exception occurs, print the error message
    print(f"Error: {e}")
    data = "Error: Failed to connect to Azure Storage."
    success_message = None
  return render_template("index.html",
                         success_message=success_message,
                         data=data,
                         secret=secret)


@app.route('/next_page')
def next():
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

  return render_template("upload.html",
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
    return redirect(url_for('next'))

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
  return redirect(url_for('next'))


@app.route('/share_blob', methods=['POST'])
def share_blob():

  permission = request.form.get('permission')
  if permission is not None:
    permission = permission.lower()
  #expiry_int = request.form.get('expiry')
  blob = request.form.get('blob_name')
  print("blob name : ", blob)

  # Get a BlobClient for the specific blob
  blob_client = blob_service_client.get_blob_client(container_name, blob)
  sas_token = generate_SAS(blob, permission)
  #print("SAS Token : ", sas_token)
  # Construct the complete URL with the SAS token
  blob_url_with_sas = f"{blob_client.url}?{sas_token}"
  print("blob_url_with_sas : ", blob_url_with_sas)
  return render_template("share_blob.html", sharelink=blob_url_with_sas)


def generate_SAS(blob, permission):
  #start_time = datetime.now()
  #expiry_time = start_time + timedelta(days=7)
  print("permisson value : ", permission)
  print(f"data type of permission is {type(permission)}")
  expiration = datetime.utcnow() + timedelta(hours=1)
  print("expiry time : ", expiration)
  print(f"data tyep of expiry_time is {type(expiration)}")
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
      permission=BlobSasPermissions(permission=True),
      expiry=expiry_time_str)
  # URL encode the SAS token
  encoded_sas_token = quote(SAS_Token)
  return encoded_sas_token


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=8080)
