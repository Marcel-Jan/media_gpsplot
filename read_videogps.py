from xml.dom import minidom
import os
import re
import pandas as pd
import folium


def geoconv_degr_dec(geodegree):
    degree, minute, second = re.split(':', geodegree)
    geodecim = float(degree) + float(minute) / 60 + float(second) / (60 * 60)
    return geodecim


geodf = pd.DataFrame(columns=['xmlfilename', 'creationdate', 'latitude', 'longitude', 'altitude'])

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
            latdecimal = geoconv_degr_dec(latitude)
            longdecimal = geoconv_degr_dec(longitude)
            print(f"latitude, longitude: {latdecimal}, {longdecimal}")
            print(f"altitude: {altitude}")
            geodf.loc[filename, :] = [filename, pd.to_datetime(creationdate), latdecimal, longdecimal, altitude]

# Find center of folium map
latitude_mean = geodf['latitude'].mean()
longitude_mean = geodf['longitude'].mean()

# Make folium map
my_map = folium.Map(location=[latitude_mean, longitude_mean], zoom_start=12)
markers = {}

# Create folium markers. With filename and creationdate in popup.
for index, georow in geodf.iterrows():
    folium.Marker([georow['latitude'], georow['longitude']], popup=f"filename: {georow['xmlfilename']}</br>creationdate: {georow['creationdate']}").add_to(my_map)

# Write html file with zoomable map
my_map.save('videogps_folium.html')
