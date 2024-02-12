from flask import Flask, render_template, redirect, request, url_for
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import os

app = Flask(__name__)

client_id = os.environ['AZURE_CLIENT_ID']
tenant_id = os.environ['AZURE_TENANT_ID']
client_secret = os.environ['AZURE_CLIENT_SECRET']
vault_url = os.environ["AZURE_VAULT_URL"]
account_url = os.environ["AZURE_STORAGE_URL"]

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
blob_name = "aaa.txt"

# Set client to access Azure Storage container
blob_service_client = BlobServiceClient(account_url=account_url,
                                        credential=blob_credentials)

# Get the container client
container_client = blob_service_client.get_container_client(
    container=container_name)


@app.route("/")
def index():
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
    print(f"blob_name: {blob_name}")
    blob_url = blob_client.url
    print(f"blob_url: {blob_urls}")
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
    blob_name = f"uploaded_files/{uploaded_file.filename}"

    # Create a BlobClient and upload the file
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(uploaded_file.stream.read(), overwrite=True)
    return redirect(url_for('next'))

  return "Hello"


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=8080)
