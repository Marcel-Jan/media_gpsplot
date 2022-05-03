from xml.dom import minidom
import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

geodf = pd.DataFrame(columns=['creationdate', 'latitude', 'longitude', 'altitude'])

path_of_the_directory= 'Z:\\Eigen video\\2021\\Vercors en Drome 2021'
print(f"Files and directories in path: {path_of_the_directory}")
ext = ".XML"
for filename in os.listdir(path_of_the_directory):
    sonyfile = os.path.join(path_of_the_directory, filename)
    if os.path.isfile(sonyfile) and sonyfile.endswith(ext):
        print(sonyfile)
        sonyxml = minidom.parse(sonyfile)
        CreationDate = sonyxml.getElementsByTagName('CreationDate')
        for createdate in CreationDate:
            print(createdate.attributes['value'].value)
            creationdate = createdate.attributes['value'].value

        Items = sonyxml.getElementsByTagName('Item')
        for elem in Items:
            # print(f"{elem.attributes['name'].value} : {elem.attributes['value'].value}")
            # if not elem.getElementsByTagName("LatitudeRef"):
            #     print("LatitudeRef not found")
            if elem.attributes['name'].value == "LatitudeRef":
                latitude_direction = elem.attributes['value'].value
            if elem.attributes['name'].value == "LongitudeRef":
                longitude_direction = elem.attributes['value'].value

            if elem.attributes['name'].value == "Latitude":
                latitude = elem.attributes['value'].value

            if elem.attributes['name'].value == "Longitude":
                longitude = elem.attributes['value'].value

            if elem.attributes['name'].value == "Altitude":
                altitude = elem.attributes['value'].value

        if 'latitude' in locals():
            # print(f"latitude: {latitude} ({latitude_direction}), longitude: {longitude} ({longitude_direction})")
            latdeg, latmin, latsec = re.split(':', latitude)
            latdecimal = float(latdeg) + float(latmin)/60 + float(latsec)/(60*60)
            longdeg, longmin, longsec = re.split(':', longitude)
            longdecimal = float(longdeg) + float(longmin)/60 + float(longsec)/(60*60)
            print(f"latitude, longitude: {latdecimal}, {longdecimal}")
            print(f"altitude: {altitude}")
            # georow = pd.Series([creationdate, latitude, longitude])
            geodf.loc[filename, :] = [pd.to_datetime(creationdate), latdecimal, longdecimal, altitude]


print(geodf)
# print(geodf.shape)
BBox = ((geodf.longitude.min(), geodf.longitude.max(),
         geodf.latitude.min(), geodf.latitude.max()))
print(BBox)
# "D:\Video\Vercors en Drome 2021\VDMmap.png"
vdm2021_m = plt.imread('D:\Video\Vercors en Drome 2021\VDMmap.png')

fig, ax = plt.subplots(figsize=(8, 7))
ax.scatter(geodf.longitude, geodf.latitude, zorder=1, c='b', s=10)
ax.set_title('Vercors en Drôme 2021')
ax.set_xlim(BBox[0], BBox[1])
ax.set_ylim(BBox[2], BBox[3])

ax.imshow(vdm2021_m, zorder=0, extent=BBox, aspect='equal')
plt.show()
