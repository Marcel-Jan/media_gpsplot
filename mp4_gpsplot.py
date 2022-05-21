import subprocess
import pandas as pd
import os
from folium import Map, Marker, Icon
from xml.etree import ElementTree as ET


class MP4File:
    def __init__(self, mp4file_location_disk, mp4file_ext):
        self.geocoordinate_in_degrees = None
        self.mp4file_location_disk = mp4file_location_disk
        self.mp4file_ext = mp4file_ext

    def mp4file_metadata(self):
        exiftool_command = ["exiftool", "-ee", "-m", "-p", "C:\\Program Files\\Exiftool\\fmt_files\\gpx.fmt",
                            self.mp4file_location_disk]
        exif_metadata = subprocess.run(exiftool_command, stdout=subprocess.PIPE)
        exif_metadata_decoded = exif_metadata.stdout.decode('utf-8')
        # print(exif_metadata_decoded)
        exif_metadata_root = ET.fromstring(exif_metadata_decoded)
        lat = None
        lon = None
        elevation = None
        measurement_time = None

        for exif_element in exif_metadata_root.iter():
            # print(f"exif_element: {exif_element}")
            if lat is not None and lon is not None and measurement_time is not None:
                print(f"lat: {lat}, lon: {lon}, elevation: {elevation}, measurement_time: {measurement_time}")
                break
            elif "trkpt" in exif_element.tag:
                lat = exif_element.attrib['lat']
                lon = exif_element.attrib['lon']
            elif "ele" in exif_element.tag:
                elevation = exif_element.text
            elif "time" in exif_element.tag:
                measurement_time = exif_element.text

        print(f"Geolocation file:{self.mp4file_location_disk}: lat: {lat}, lon: {lon}, elevation: {elevation},"
              f" measurement_time: {measurement_time}")
        if lat is not None and lon is not None and elevation is None:
            # print("Got lat, lon, but no elevation")
            return lat, lon, 0, measurement_time
        elif lat is not None and lon is not None and elevation is not None:
            # print("Got lat, lon, and elevation")
            return lat, lon, elevation, measurement_time
        else:
            pass


if __name__ == "__main__":
    mediaext_to_find = [".MTS"]

    mp4video_location_disk = 'Z:\\2013'

    mp4videodf = pd.DataFrame(columns=['filename', 'creationdate', 'latitude', 'longitude', 'altitude'])
    mp4video_ext = ".MTS"

    for root, dirs, filenames in os.walk(mp4video_location_disk):
        # print(f"root: {root}, dirs: {dirs}, filenames: {filenames}")
        for filename in filenames:
            path_and_file_in_video_dir = os.path.join(root, filename)
            if os.path.isfile(path_and_file_in_video_dir) and \
                    (path_and_file_in_video_dir.endswith(mp4video_ext)
                     or path_and_file_in_video_dir.endswith(mp4video_ext.lower())):
                print(f"path_and_file_in_video_dir: {path_and_file_in_video_dir}")

                try:
                    mp4file = MP4File(path_and_file_in_video_dir, mp4video_ext)
                    latitude, longitude, altitude, frametime = mp4file.mp4file_metadata()
                    mp4videodf.loc[path_and_file_in_video_dir, :] = [filename, pd.to_datetime(frametime),
                                                                     float(latitude), float(longitude), float(altitude)]
                except TypeError:
                    pass

    print(mp4videodf)

    # Find center of folium map
    latitude_mean = mp4videodf['latitude'].mean()
    longitude_mean = mp4videodf['longitude'].mean()

    # Make folium map
    my_map = Map(location=[latitude_mean, longitude_mean], zoom_start=12)

    # Create folium markers. With filename and creationdate in popup.
    for index, georow in mp4videodf.iterrows():
        Marker([georow['latitude'], georow['longitude']],
               popup=f"filename: {georow['filename']}</br>datetime: {georow['creationdate']}",
               # popup=f"creationdate: {georow['creationdate']}",
               icon=Icon(color='blue', icon_color='white', icon='facetime-video')).add_to(my_map)

    my_map.save(f'{mp4video_location_disk}/mp4_gpsplot.html')
