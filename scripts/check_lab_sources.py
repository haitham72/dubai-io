import os

sources_dir = r"G:\Haitham\lab-data\comparison\sources"
if os.path.exists(sources_dir):
    print("Files in comparison/sources:")
    for f in os.listdir(sources_dir):
        fp = os.path.join(sources_dir, f)
        print(f"  {f} ({os.path.getsize(fp):,} bytes)")

weeks_dir = r"G:\Haitham\lab-data\mamty-hindsight\weeks"
if os.path.exists(weeks_dir):
    weeks = os.listdir(weeks_dir)
    print(f"Total weeks in mamty-hindsight/weeks: {len(weeks)}")
    print(f"Sample recent weeks: {sorted(weeks)[-5:]}")
