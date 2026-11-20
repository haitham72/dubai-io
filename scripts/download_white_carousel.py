import urllib.request
import os

url = "https://d8j0ntlcm91z4.cloudfront.net/user_37CCPXDdxsgwGNn2frvHwfIdxWI/hf_20261120_074356_a4cc04fa-839d-4606-85ac-e4d316ed3e01.png"
dest = r"design\references\quest\generated\white_1card_carousel.png"
urllib.request.urlretrieve(url, dest)
print(f"Downloaded to {dest} ({os.path.getsize(dest):,} bytes)")
