from flask import Flask, render_template
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


@app.route("/")
def route():
  try:
    # Set client to access Azure Storage container
    blob_service_client = BlobServiceClient(account_url=account_url,
                                            credential=blob_credentials)

    # Get the container client
    container_client = blob_service_client.get_container_client(
        container=container_name)
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


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=8080)
