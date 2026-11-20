import urllib.request
import os

url = "https://d8j0ntlcm91z4.cloudfront.net/user_37CCPXDdxsgwGNn2frvHwfIdxWI/hf_20261120_073657_e67149e6-30a8-4670-8575-c585333bd63d.png"
dest = r"design\references\quest\generated\nano_banana_3_4_carousel_concept.png"
os.makedirs(os.path.dirname(dest), exist_ok=True)
urllib.request.urlretrieve(url, dest)
print(f"Downloaded to {dest} ({os.path.getsize(dest):,} bytes)")
