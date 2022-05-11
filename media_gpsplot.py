from xml.dom import minidom
import os
import re
import pandas as pd
import folium
from folium import IFrame
from PIL import Image
from PIL.ExifTags import GPSTAGS
from PIL.ExifTags import TAGS
import base64
import argparse


class VideoFile:
    def __init__(self, videofile_location_disk):
        self.geocoordinate_in_degrees = None
        self.videofile_location_disk = videofile_location_disk
        self.videofile_creationdate = self.video_creationdate
        self.videofile_geolocation = self.video_geocoordinates

    def convert_sony_geocoordinate_to_decimals(self, geocoordinate_in_degrees):
        print(f"geocoordinate_in_degrees: {geocoordinate_in_degrees}")
        degree, minute, second = re.split(':', geocoordinate_in_degrees)
        geocoordinates_in_decimals = float(degree) + float(minute) / 60 + float(second) / (60 * 60)
        return geocoordinates_in_decimals

    def video_metadata(self):
        video_metadata = minidom.parse(self.videofile_location_disk)
        return video_metadata

    def video_creationdate(self):
        # Get XML data
        video_metadata = self.video_metadata()
        video_creationdates = video_metadata.getElementsByTagName('CreationDate')
        for video_creationdate_item in video_creationdates:
            print(video_creationdate_item.attributes['value'].value)
            video_creationdate = video_creationdate_item.attributes['value'].value
        return video_creationdate

    def video_geocoordinates(self):
        # Get XML data
        global altitude_direction
        gpscoordinates_exist = None
        video_latitude = None
        video_longitude = None
        video_altitude = None
        video_geolocation = None
        video_metadata = self.video_metadata()
        video_metadata_items = video_metadata.getElementsByTagName('Item')
        count_latitude_elements = 0
        for video_metadata_element in video_metadata_items:
            if video_metadata_element.attributes['name'].value == "LatitudeRef":
                latitude_direction = video_metadata_element.attributes['value'].value
            if video_metadata_element.attributes['name'].value == "LongitudeRef":
                longitude_direction = video_metadata_element.attributes['value'].value
            if video_metadata_element.attributes['name'].value == "AltitudeRef":
                altitude_direction = video_metadata_element.attributes['value'].value

            if video_metadata_element.attributes['name'].value == "Latitude":
                count_latitude_elements += 1
                gpscoordinates_exist = True
                print(f"latitude: {video_metadata_element.attributes['value'].value}")
                video_latitude = video_metadata_element.attributes['value'].value

            if video_metadata_element.attributes['name'].value == "Longitude":
                print(f"longitude: {video_metadata_element.attributes['value'].value}")
                video_longitude = video_metadata_element.attributes['value'].value

            if video_metadata_element.attributes['name'].value == "Altitude":
                print(f"altitude: {video_metadata_element.attributes['value'].value}")
            video_altitude = video_metadata_element.attributes['value'].value

        print(f"count_latitude_elements: {count_latitude_elements}")
        if count_latitude_elements == 0:
            gpscoordinates_exist = False

        print(f"gpscoordinates_exist: {gpscoordinates_exist}")
        if gpscoordinates_exist is True:
            if 'video_latitude' in locals() and gpscoordinates_exist is True:
                latdecimal = self.convert_sony_geocoordinate_to_decimals(video_latitude)
                longdecimal = self.convert_sony_geocoordinate_to_decimals(video_longitude)
                # print(f"altitude_direction: {altitude_direction}")
                # print(f"video_altitude: {video_altitude}")
                if altitude_direction == 0:
                    video_altitude = float(video_altitude)
                else:
                    # Below sea level
                    video_altitude = -float(video_altitude)

                # print(f"latitude, longitude: {latdecimal}, {longdecimal}")

                video_geolocation = (latdecimal, longdecimal, video_altitude)
                print(f"geolocation: {video_geolocation}")
            return video_geolocation
        else:
            return None


class PhotoFile:
    def __init__(self, photofile_location_disk, photofile_type):
        self.geocoordinate_in_degrees = None
        self.photofile_location_disk = photofile_location_disk
        self.photofile_type = photofile_type
        if photofile_type == 'JPG':
            self.photofile_creationdate = self.photo_creationdate
            self.photofile_geolocation = self.photo_geocoordinates

    def convert_exif_geocoordinate_to_decimals(self, geocoordinate_in_degrees, reference):
        geocoordinates_in_decimals = float(geocoordinate_in_degrees[0]) + \
                                     float(geocoordinate_in_degrees[1]) / 60 + \
                                     float(geocoordinate_in_degrees[2]) / (60 * 60)
        if reference in ['S', 'W']:
            geocoordinates_in_decimals = geocoordinates_in_decimals * -1
        return geocoordinates_in_decimals

    def exif(self):
        image = Image.open(self.photofile_location_disk)
        image.verify()
        return image._getexif()

    def exif_labeled(self):
        labeled = {}
        for (key, val) in self.exif().items():
            labeled[TAGS.get(key)] = val
        return labeled

    def get_geotagging(self):
        if not self.exif():
            print("No EXIF metadata found")

        geotagging = {}
        for (idx, tag) in TAGS.items():
            if tag == 'GPSInfo':
                if idx not in self.exif():
                    print("No EXIF geotagging found")

                for (key, val) in GPSTAGS.items():
                    if key in self.exif()[idx]:
                        geotagging[val] = self.exif()[idx][key]
        return geotagging

    def photo_creationdate(self):
        # Get XML data
        photo_metadata = self.exif_labeled()
        photo_creationdate = photo_metadata["DateTime"]
        # print(f"photo_creationdate: {photo_creationdate}")
        return photo_creationdate

    def photo_geocoordinates(self):
        # Get XML data
        gpscoordinates_exist = None
        photo_latitude = None
        photo_longitude = None
        photo_altitude = None
        photo_geolocation = None
        photo_metadata = self.photo_creationdate

        try:
            jpggeotags = self.get_geotagging()
            photo_latitude = self.convert_exif_geocoordinate_to_decimals(jpggeotags['GPSLatitude'],
                                                                         jpggeotags['GPSLatitudeRef'])
            photo_longitude = self.convert_exif_geocoordinate_to_decimals(jpggeotags['GPSLongitude'],
                                                                          jpggeotags['GPSLatitudeRef'])
            if jpggeotags["GPSAltitudeRef"] == b'\x00':
                photo_altitude = float(jpggeotags["GPSAltitude"])
            else:
                # Below sea level
                photo_altitude = -float(jpggeotags["GPSAltitude"])
            return photo_latitude, photo_longitude, photo_altitude
        except:
            pass


def make_popup_imgtag(popup_image):
    encoded = base64.b64encode(open(popup_image, 'rb').read())
    html = '<img src="data:image/png;base64,{}" width="400" height="300">'.format
    iframe = IFrame(html(encoded.decode('UTF-8')), width=400, height=300)
    popup = folium.Popup(iframe, max_width=400)
    return html, iframe, popup


if __name__ == "__main__":
    video_location_disk = 'Z:\\2021\\Vercors en Drome 2021'
    photo_location_disk = 'Y:\\2021\\Vercors en Drome 2021\\iPhone'
    video_ext = ".XML"

    videodf = pd.DataFrame(columns=['filename', 'creationdate', 'latitude', 'longitude', 'altitude'])
    for filename_in_video_dir in os.listdir(video_location_disk):
        path_and_file_in_video_dir = os.path.join(video_location_disk, filename_in_video_dir)

        # Check that file is XML file
        if os.path.isfile(path_and_file_in_video_dir) and \
                (path_and_file_in_video_dir.endswith(video_ext) or
                 path_and_file_in_video_dir.endswith(video_ext.lower())):
            print(path_and_file_in_video_dir)
            video = VideoFile(path_and_file_in_video_dir)
            print(f"video.geolocation: {video.video_geocoordinates()}")
            if video.video_geocoordinates() is not None:
                latitude, longitude, altitude = video.video_geocoordinates()
                videodf.loc[filename_in_video_dir, :] = [filename_in_video_dir,
                                                         pd.to_datetime(video.videofile_creationdate()),
                                                         latitude, longitude, altitude]

    print(videodf)

    # JPG geocoordinates
    photodf = pd.DataFrame(columns=['filename', 'creationdate', 'latitude', 'longitude', 'altitude'])
    print(f"Path photo JPG files: {photo_location_disk}")
    jpg_ext = ".JPG"
    for filename in os.listdir(photo_location_disk):
        path_and_file_in_photo_dir = os.path.join(photo_location_disk, filename)
        if os.path.isfile(path_and_file_in_photo_dir) and \
                (path_and_file_in_photo_dir.endswith(jpg_ext) or path_and_file_in_photo_dir.endswith(jpg_ext.lower())):
            print(f"path_and_file_in_photo_dir: {path_and_file_in_photo_dir}")
            photo = PhotoFile(path_and_file_in_photo_dir, 'JPG')
            print(f"photo.photo_creationdate: {photo.photo_creationdate()}")
            if photo.photo_geocoordinates() is not None:
                print(f"photo.photo_geocoordinates: {photo.photo_geocoordinates()}")
                latitude, longitude, altitude = photo.photo_geocoordinates()
                photodf.loc[filename, :] = [filename, photo.photo_creationdate(), latitude, longitude, altitude]

    print(photodf)

    # Find center of folium map
    latitude_mean = videodf['latitude'].mean()
    longitude_mean = videodf['longitude'].mean()

    # Make folium map
    my_map = folium.Map(location=[latitude_mean, longitude_mean], zoom_start=12)

    # Create folium markers. With filename and creationdate in popup.
    for index, georow in videodf.iterrows():
        folium.Marker([georow['latitude'], georow['longitude']],
                      popup=f"filename: {georow['filename']}</br>creationdate: {georow['creationdate']}"
                      , icon=folium.Icon(color='blue', icon_color='white', icon='facetime-video')).add_to(my_map)

    for index, georow in photodf.iterrows():
        folium.Marker([georow['latitude'], georow['longitude']]
                      , popup=f"filename: {georow['filename']}</br>creationdate: {georow['creationdate']}"
                      , icon=folium.Icon(color='red', icon_color='white', icon='camera')).add_to(my_map)

    popup_image = "Y:\\2021\\Vercors en Drome 2021\\iPhone\\IMG_3474.JPG"
    popup_html, popup_iframe, popup_text = make_popup_imgtag(popup_image)

    folium.Marker(location=[44.69158611111111, 5.986177777777778], tooltip=popup_html, popup=popup_text,
                  icon=folium.Icon(color='gray', icon_color='white', icon='camera')).add_to(my_map)

    my_map.save('media_gpsplot.html')
