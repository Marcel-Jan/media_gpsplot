""" Creates a map with markers for video and photo files with geolocation data.

Returns:
    html file: media_gpsplot.html which contains a map with markers for
      video and photo files with geolocation data.

"""

import argparse
from xml.dom import minidom
import os
import re
from pathlib import Path
import datetime
import logging
import pandas as pd
import folium
# from folium import IFrame
import PIL
from PIL import Image
from PIL.ExifTags import TAGS
# import base64
import pillow_heif
import piexif



class HEICFile:
    """ HEICFile class

        Class for .heic files.
    """
    def __init__(self, mediafile_location_disk, logger):
        self.geocoordinate_in_degrees = None
        self.mediafile_location_disk = mediafile_location_disk
        logger.debug('mediafile_location_disk: %s', mediafile_location_disk)
        logger.debug('Run method: get_exif_from_heic')
        self.heic_metadata = self.get_exif_from_heic(mediafile_location_disk, logger)
        logger.debug('Run method: mediafile_creationdate')
        self.mediafile_creationdate = self.get_creationdate_from_heic(self.heic_metadata)
        logger.debug('Run method: get_geotagging_from_heic')
        self.mediafile_geodata = self.get_geotagging_from_heic(self.heic_metadata)
        logger.debug('Run method: get_geocoordinates_from_heic')
        self.mediafile_geolocation = self.get_geocoordinates_from_heic(self.mediafile_geodata)

    def convert_heic_geocoordinate_to_decimals(self, geo_degrees, geo_minutes,
                                            geo_seconds, reference):
        """ Converts geocoordinates in degrees, minutes, seconds to decimals.
            Example GPSLatitude format from HEIC files:
            GPSLatitude: ((45, 1), (4, 1), (870, 100))
            Latitude in degrees: 45/1, (4/1 + 870/100/60) = 45, 4.145

        Args:
            geo_degrees (float): geo coordinate in degrees
            geo_minutes (float): geo coordinate in minutes
            geo_seconds (float): geo coordinate in seconds
            reference (str): 'N', 'S', 'E' or 'W'

        Returns:
            geocoordinates_in_decimals: geo coordinate in decimals
        """
        # print("Method: convert_heic_geocoordinate_to_decimals")
        geocoordinates_in_decimals = float(geo_degrees) + \
            float(geo_minutes) / 60 + \
            float(geo_seconds) / (60 * 60)
        # Southern or Western hemisphere needs to be negative
        # Had to add b'W' and b'S' to the list of references because
        # the reference is sometimes a byte string
        if reference in ['S', 'W', b'S', b'W']:
            geocoordinates_in_decimals = geocoordinates_in_decimals * -1
        return geocoordinates_in_decimals


    def get_exif_from_heic(self, mediafile_location_disk, logger):
        """ Gets EXIF data from HEIC file.

        Args:
            mediafile_location_disk (str): path and name of HEIC file

        Returns:
            dict: EXIF data
        """
        # print("Supported:", pillow_heif.is_supported(mediafile_location_disk))
        logger.debug('Supported: %s', pillow_heif.is_supported(mediafile_location_disk))
        # print("Mime:", pillow_heif.get_file_mimetype(mediafile_location_disk))
        logger.debug('Mime: %s', pillow_heif.get_file_mimetype(mediafile_location_disk))
        try:
            heic_file = pillow_heif.open_heif(mediafile_location_disk, convert_hdr_to_8bit=False)
        except PIL.UnidentifiedImageError:
            print("Unidentified Image Error")
            return None
        except PIL.Image.DecompressionBombError:
            print("Decompression Bomb Error")
            return None
        except AttributeError:
            return None
        for image in heic_file:
            if image.info.get("exif", None):
                exif_dict = piexif.load(image.info["exif"], key_is_name=True)
        return exif_dict


    def get_geotagging_from_heic(self, heif_exif_dict):
        """ Gets geotagging data from HEIC file.

        Args:
            mediafile_location_disk (str): path and name of HEIC file

        Returns:
            dict: geotagging data
        """
        if not heif_exif_dict:
            print("No EXIF metadata found")

        # Check GPS key exists in heif_exif_dict
        if "GPS" in heif_exif_dict.keys():
            # print(f"value: {heif_exif_dict['GPS']}")
            gpscoordinates = heif_exif_dict['GPS']
        else:
            gpscoordinates = None
        return gpscoordinates


    def get_geocoordinates_from_heic(self, gpscoordinates_from_heic):
        """ Gets geocoordinates from HEIC file.

        Args:
            gpscoordinates_from_heic (_type_): _description_

        Returns:
            float: gps_lat_decimals, 
            float: gps_long_decimals, 
            float: gps_alt_decimals
        """
        # Check that GPS data exists
        if (gpscoordinates_from_heic is None or gpscoordinates_from_heic=={}):
            return None
        # print(f"gpscoordinates_from_heic: {gpscoordinates_from_heic}")
        gps_lat_degrees = gpscoordinates_from_heic['GPSLatitude'][0][0] \
                               / float(gpscoordinates_from_heic['GPSLatitude'][0][1])
        gps_lat_minutes = gpscoordinates_from_heic['GPSLatitude'][1][0] \
                               / float(gpscoordinates_from_heic['GPSLatitude'][1][1])
        gps_lat_seconds = gpscoordinates_from_heic['GPSLatitude'][2][0] \
                               / float(gpscoordinates_from_heic['GPSLatitude'][2][1])
        gps_lat_ref = gpscoordinates_from_heic['GPSLatitudeRef']
        gps_long_degrees = gpscoordinates_from_heic['GPSLongitude'][0][0] \
                                / float(gpscoordinates_from_heic['GPSLongitude'][0][1])
        gps_long_minutes = gpscoordinates_from_heic['GPSLongitude'][1][0] \
                                / float(gpscoordinates_from_heic['GPSLongitude'][1][1])
        gps_long_seconds = gpscoordinates_from_heic['GPSLongitude'][2][0] \
                                / float(gpscoordinates_from_heic['GPSLongitude'][2][1])
        gps_long_ref = gpscoordinates_from_heic['GPSLongitudeRef']
        # Sometimes the GPSAltitude key is missing
        if "GPSAltitude" in gpscoordinates_from_heic.keys():
            gps_altitude = gpscoordinates_from_heic['GPSAltitude']
        else:
            gps_altitude = (0, 1)

        if "GPSAltitudeRef" in gpscoordinates_from_heic.keys():
            gps_alt_ref = gpscoordinates_from_heic['GPSAltitudeRef']
        else:
            gps_alt_ref = 0

        gps_lat_decimals = self.convert_heic_geocoordinate_to_decimals(gps_lat_degrees,
                                                                          gps_lat_minutes,
                                                                          gps_lat_seconds,
                                                                          gps_lat_ref)
        gps_long_decimals = self.convert_heic_geocoordinate_to_decimals(gps_long_degrees,
                                                                    gps_long_minutes,
                                                                    gps_long_seconds,
                                                                    gps_long_ref)
        # GPSAltitudeRef = 0 means above sea level
        if gps_alt_ref == 0:
            gps_alt_decimals = float(gps_altitude[0]) / float(gps_altitude[1])
        elif gps_alt_ref == 1:
            gps_alt_decimals = (float(gps_altitude[0]) / float(gps_altitude[1])) * -1

        gps_alt_decimals = (float(gps_altitude[0]) / float(gps_altitude[1]))
        print(f"Latitude: {gps_lat_decimals}, Longitude: " \
              f"{gps_long_decimals}, Altitude: {gps_alt_decimals}")
        return gps_lat_decimals, gps_long_decimals, gps_alt_decimals


    def get_creationdate_from_heic(self, heif_exif_dict):
        """ Get the creationdate from HEIC file.

        Args:
            heif_exif_dict (dict): Dictionary with all the EXIF data from the HEIC file

        Returns:
            str: creationdate of HEIC file
        """
        if heif_exif_dict['0th'] is not None and "DateTime" in heif_exif_dict['0th'].keys():
            heic_creationdate = heif_exif_dict['0th']["DateTime"].decode('UTF-8')
            return heic_creationdate

# End of class HEICFile


class MP4XMLFile:
    """ Class for XML files accompanying MP4 files.  
    """
    def __init__(self, mediafile_location_disk, logger):
        self.geocoordinate_in_degrees = None
        self.mediafile_location_disk = mediafile_location_disk
        logger.debug('mediafile_location_disk: %s', mediafile_location_disk)
        # print(f"mediafile_location_disk: {mediafile_location_disk}")
        logger.debug("Run method: get_metadata_from_xml")
        xml_metadata = self.get_metadata_from_xml(mediafile_location_disk)
        logger.debug("Run method: get_creationdate")
        self.mediafile_creationdate = self.get_creationdate(xml_metadata)
        logger.debug("Run method: get_geocoordinates_from_metadata")
        self.mediafile_geolocation = self.get_geocoordinates_from_metadata(xml_metadata)

    def convert_geocoordinate_to_decimals(self, geocoordinate_in_degrees, reference):
        """ convert_sony_geocoordinate_to_decimals
            Converts geocoordinates in degrees, minutes, seconds to decimals.

        Args:
            geocoordinate_in_degrees (str): string with geocoordinates in degrees, 
                                            minutes, seconds

        Returns:
            float: geo coordinate in decimals
        """
        # print(f"geocoordinate_in_degrees: {geocoordinate_in_degrees}")
        degree, minute, second = re.split(':', geocoordinate_in_degrees)
        geocoordinates_in_decimals = float(degree) + float(minute) / 60 + float(second) / (60 * 60)
        if reference in ['S', 'W']:
            geocoordinates_in_decimals = geocoordinates_in_decimals * -1
        return geocoordinates_in_decimals

    def get_metadata_from_xml(self, mediafile_location_disk):
        """ video_metadata

        Returns:
            dict: XML data from video file
        """
        print(f"mediafile_location_disk: {mediafile_location_disk}")
        # print(f"type of mediafile_location_disk: {type(mediafile_location_disk)}")
        # Convert Path object to string
        # To prevent this error: AttributeError: 'PosixPath' object has no attribute 'read'
        mediafile_location_disk_str = str(mediafile_location_disk)
        video_metadata = minidom.parse(mediafile_location_disk_str)
        return video_metadata

    def get_creationdate(self, video_metadata):
        """ video_creationdate

        Returns:
            str: creationdate of video file
        """
        video_creationdates = video_metadata.getElementsByTagName('CreationDate')
        for video_creationdate_item in video_creationdates:
            print(video_creationdate_item.attributes['value'].value)
            video_creationdate = video_creationdate_item.attributes['value'].value
        print(f"video_creationdate: {video_creationdate}")
        return video_creationdate

    def get_geocoordinates_from_metadata(self, video_metadata):
        """ video_geocoordinates

        Returns:
            tuple: latitude, longitude, altitude of video file
        """
        # Get XML data
        global altitude_direction
        gpscoordinates_exist = None
        video_latitude = None
        video_longitude = None
        video_altitude = None
        video_geolocation = None
        video_metadata_items = video_metadata.getElementsByTagName('Item')
        count_latitude_elements = 0
        for video_metadata_element in video_metadata_items:
            if video_metadata_element.attributes['name'].value == "AltitudeRef":
                altitude_direction = video_metadata_element.attributes['value'].value

                # make sure altitude_direction is an integer
                altitude_direction = int(altitude_direction)

            if video_metadata_element.attributes['name'].value == "Latitude":
                count_latitude_elements += 1
                gpscoordinates_exist = True
                video_latitude = video_metadata_element.attributes['value'].value

            if video_metadata_element.attributes['name'].value == "LatitudeRef":
                video_latituderef = video_metadata_element.attributes['value'].value
                print(f"video_latituderef: {video_latituderef}")

            if video_metadata_element.attributes['name'].value == "Longitude":
                video_longitude = video_metadata_element.attributes['value'].value

            if video_metadata_element.attributes['name'].value == "LongitudeRef":
                video_longituderef = video_metadata_element.attributes['value'].value

            if video_metadata_element.attributes['name'].value == "Altitude":
                video_altitude = video_metadata_element.attributes['value'].value

        # print(f"Latitude: {video_latitude}, Longitude: {video_longitude}, Altitude: {video_altitude}, AltitudeRef: {altitude_direction}")

        # print(f"count_latitude_elements: {count_latitude_elements}")
        if count_latitude_elements == 0:
            gpscoordinates_exist = False

        print(f"gpscoordinates_exist: {gpscoordinates_exist}")
        if gpscoordinates_exist is True:
            if 'video_latitude' in locals() and gpscoordinates_exist is True:
                latdecimal = self.convert_geocoordinate_to_decimals(video_latitude, video_latituderef)
                longdecimal = self.convert_geocoordinate_to_decimals(video_longitude, video_longituderef)
                # Sometimes only the altitude is missing
                if video_altitude is None:
                    video_altitude = 0

                if altitude_direction == 0:
                    video_altitude_float = float(video_altitude)
                elif altitude_direction == 1:
                    # Below sea level
                    video_altitude_float = -float(video_altitude)
                else:
                    video_altitude_float = 0

                video_geolocation = (latdecimal, longdecimal, video_altitude_float)
                print(f"geolocation: {video_geolocation}")
            return video_geolocation
        else:
            return None

# End of class MP4XMLFile


class JpegFile:
    """ JpegFile class
    """
    def __init__(self, mediafile_location_disk, logger):
        # self.geocoordinate_in_degrees = None
        # self.mediafile_location_disk = mediafile_location_disk
        # self.mediafile_type = photofile_type
        # self.photofile_creationdate = self.photo_creationdate
        # self.photofile_geolocation = self.photo_geocoordinates

        self.geocoordinate_in_degrees = None
        self.mediafile_location_disk = mediafile_location_disk
        logger.debug('mediafile_location_disk: %s', mediafile_location_disk)
        print(f"mediafile_location_disk: {mediafile_location_disk}")
        logger.debug('Run JpegFile method: get_exif_from_jpeg')
        self.mediafile_metadata = self.get_exif_from_jpeg(mediafile_location_disk, logger)
        logger.debug('Run JpegFile method: get_exif_labeled')
        self.jpeg_metadata_labeled = self.get_exif_labeled(self.mediafile_metadata, logger)
        logger.debug('Run JpegFile method: mediafile_creationdate')
        self.mediafile_creationdate = self.get_creationdate_from_jpeg(self.jpeg_metadata_labeled)
        # print(f"self.jpeg_metadata_labeled: {self.jpeg_metadata_labeled}")
        if self.jpeg_metadata_labeled is not None:
            if 'GPSInfo' in self.jpeg_metadata_labeled:
                logger.debug('Run JpegFile method: get_geocoordinates_from_jpeg')
                self.mediafile_geolocation = self.get_geocoordinates_from_jpeg( \
                    self.jpeg_metadata_labeled)
            else:
                self.mediafile_geolocation = None
        else:
            self.mediafile_geolocation = None

    def convert_exif_geocoordinate_to_decimals(self, geocoordinate_in_degrees, reference):
        """ Convert geocoordinates in degrees, minutes, seconds to decimals.

        Args:
            geocoordinate_in_degrees (list): geo coordinate in degrees, minutes, seconds
            reference (str): 'N', 'S', 'E' or 'W'

        Returns:
            float: geo coordinate in decimals
        """ 
        geocoordinates_in_decimals = float(geocoordinate_in_degrees[0]) + \
                                     float(geocoordinate_in_degrees[1]) / 60 + \
                                     float(geocoordinate_in_degrees[2]) / (60 * 60)
        # Southern or Western hemisphere needs to be negative
        # Had to add b'W' and b'S' to the list of references because
        # the reference is sometimes a byte string
        if reference in ['S', 'W', b'S', b'W']:
            geocoordinates_in_decimals = geocoordinates_in_decimals * -1
        return geocoordinates_in_decimals

    def get_exif_from_jpeg(self, mediafile_location_disk, logger):
        """ Gets EXIF data from JPG file.

        Returns:
            dict: EXIF data
        """
        logger.debug('JpegFile Method: get_exif_from_jpeg')
        try:
            image = Image.open(mediafile_location_disk)
            image.verify()
            jpeg_exif = image._getexif()
            # print(f"jpeg_exif: {jpeg_exif}")
            return jpeg_exif
        except PIL.UnidentifiedImageError:
            print("Unidentified Image Error")
            return None
        except PIL.Image.DecompressionBombError:
            print("Decompression Bomb Error")
            return None
        except AttributeError:
            return None

    def get_exif_labeled(self, jpeg_metadata, logger):
        """ Gets EXIF data from JPG file and labels it.

        Returns:
            dict: EXIF data with labels
        """
        logger.debug('JpegFile Method: get_exif_labeled')
        labeled = {}
        if jpeg_metadata is not None:
            for (key, val) in jpeg_metadata.items():
                labeled[TAGS.get(key)] = val
            # print(f"labeled: {labeled}")
            return labeled
        else:
            return None

    def get_creationdate_from_jpeg(self, jpeg_metadata_labeled):
        """ Gets creationdate from JPG file.

        Returns:
            str: creationdate of JPG file
        """
        # Get XML data
        photo_metadata = jpeg_metadata_labeled
        if photo_metadata is not None and "DateTime" in photo_metadata.keys():
            photo_creationdate = photo_metadata["DateTime"]
            return photo_creationdate
        else:
            return None

    def get_geocoordinates_from_jpeg(self, jpeg_metadata_labeled):
        """ Gets geocoordinates from JPG file.

        Returns:
            float: latitude,
            float: longitude,
            float: altitude of JPG file
        """        
        # Get XML data
        photo_latitude = None
        photo_longitude = None
        photo_altitude = None

        try:
            jpggeotags = jpeg_metadata_labeled['GPSInfo']
            photo_latitude = \
                self.convert_exif_geocoordinate_to_decimals(jpggeotags['GPSLatitude'],
                                                            jpggeotags['GPSLatitudeRef'])
            photo_longitude = \
                self.convert_exif_geocoordinate_to_decimals(jpggeotags['GPSLongitude'],
                                                            jpggeotags['GPSLongitudeRef'])
            if jpggeotags["GPSAltitudeRef"] == b'\x00':
                photo_altitude = float(jpggeotags["GPSAltitude"])
            else:
                # Below sea level
                photo_altitude = -float(jpggeotags["GPSAltitude"])
            return photo_latitude, photo_longitude, photo_altitude
        except:
            pass

# End of class PhotoFile

def get_coordinates_from_media_files(media_files, extension, logger):
    """ Gets geocoordinates for media files.

    Args:
        media_files (list): List of media files
        extension (str): File extension.
        logger (logger thing): logger

    Returns:
        dataframe: Dataframe with geocoordinates from XML files
    """
    logger.info('Method: get_coordinates_from_media_files')
    extension_with_dot = f".{extension}"
    # Filter files with specific extension
    filtered_media_files = [media_file for media_file in media_files \
                        if media_file.suffix.lower() == extension_with_dot]
    # Create list of objects of class depending on extension
    if extension == "xml" or extension == "XML":
        filtered_media_objects = [MP4XMLFile(media_file, logger) \
                                  for media_file in filtered_media_files]
    elif extension == "heic" or extension == "HEIC":
        filtered_media_objects = [HEICFile(media_file, logger) \
                                  for media_file in filtered_media_files]
    elif extension == "jpeg" or extension == "jpg":
        filtered_media_objects = [JpegFile(media_file, logger) \
                                  for media_file in filtered_media_files]

    # Create list of filenames for the index of the data frame
    filtered_media_files_list = [media_file.mediafile_location_disk \
                                 for media_file in filtered_media_objects]
    logging.debug('filtered_media_files_list: %s', filtered_media_files_list)

    # Create dataframe for media files with geolocation data
    media_files_df = pd.DataFrame(columns=["creationdate", "latitude", "longitude", "altitude"], \
                                  index=[filtered_media_files_list])
    # Go through filtered media files and add geolocation data to dataframe
    for media_file_object in filtered_media_objects:
        logger.debug('media_file_object.mediafile_geolocation: %s' \
                     , media_file_object.mediafile_geolocation)
        # If mediafile_geolocation is NaN, skip this file
        if media_file_object.mediafile_geolocation is None:
            print(f"Skipping {media_file_object.mediafile_location_disk}")
            logger.debug('Skipping %s', media_file_object.mediafile_location_disk)
        else:
            # Add geo data to dataframe
            logger.debug('media_file_xml.mediafile_geolocation: %s', \
                         media_file_object.mediafile_geolocation)
            media_files_df = pd.concat([media_files_df, pd.DataFrame([[ \
                media_file_object.mediafile_creationdate, \
                media_file_object.mediafile_geolocation[0], \
                media_file_object.mediafile_geolocation[1], \
                media_file_object.mediafile_geolocation[2]]], \
                columns=["creationdate", "latitude", "longitude", "altitude"], \
                index=[media_file_object.mediafile_location_disk])])

    logger.debug('media_files_df: %s', media_files_df)
    return media_files_df


def plot_map(media_files_df, output_file, logger):
    """ Plots a map with markers for media files with geolocation data.

    Args:
        media_files_df (dataframe): Dataframe with media files and geolocation data
        output_file (str): Name of output file
        logger (logger thing): logger
    """
    logger.info('Method: plot_map')
    # Find center of folium map
    latitude_mean = media_files_df['latitude'].mean()
    longitude_mean = media_files_df['longitude'].mean()

    # Make folium map
    my_map = folium.Map(location=[latitude_mean, longitude_mean], zoom_start=12)

    # Create folium markers. With filename and creationdate in popup.
    for index, georow in media_files_df.iterrows():
        # Get extension of filename from the (POSIX) index
        # print(f"index: {index}")
        extension = str(index).split(".")[1].split("'")[0].lower()
        # print(f"extension: {extension}")

        if extension == "heic":
            marker_colour = 'red'
            marker_icon = 'camera'
        elif extension == "jpg" or \
             extension == "jpeg":
            marker_colour = 'darkred'
            marker_icon = 'camera'
        elif extension == "mp4":
            marker_colour = 'blue'
            marker_icon = 'facetime-video'
        elif extension == "mp4" or extension == "xml":
            marker_colour = 'blue'
            marker_icon = 'facetime-video'
        elif extension == "mts":
            marker_colour = 'darkblue'
            marker_icon = 'facetime-video'
        else:
            marker_colour = 'lightgray'
            marker_icon = 'question-sign'
        logger.debug('marker_colour: %s, marker_icon: %s', marker_colour, marker_icon)
        logger.debug('georow[latitude]: %s, georow[longitude]: %s, georow[creationdate]: %s', \
                        georow['latitude'], georow['longitude'], georow['creationdate'])

        if pd.isna(georow['latitude']) or \
           pd.isna(georow['longitude']) or \
           georow['latitude'] == "nan" or \
           georow['longitude'] == "nan":
            print(f"Skipping {index}")
            logger.debug('Skipping %s', index)
        else:
            folium.Marker([georow['latitude'], georow['longitude']],
                          popup=f"filename: {index}</br> " \
                                f"creationdate: {georow['creationdate']}", \
                          icon=folium.Icon(color=marker_colour, \
                                            icon_color='white', \
                                            icon=marker_icon) \
                        ).add_to(my_map)

    my_map.save(f'{output_file}')


def main():
    """ Main function of the program.
    """

    basedir = os.path.abspath(os.path.dirname(__file__))


    # Set up logging
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

    file_handler = logging.FileHandler(f'{basedir}/log/media_gpsplot3_' \
                                    f'{datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

    logger.debug('Start of media_gpsplot3.py')
    logger.debug('===============================')
    logger.debug('basedir: %s', basedir)


    parser = argparse.ArgumentParser(
        description="This program gets geolocations from media files" \
                    " and plots them on a map in html format."
    )
    parser.add_argument(
        "--media_path", "-m", type=str,
        help="Path(s) of media files. Multiple paths are comma separated." \
             " Default: current directory",
        default="."
    )
    parser.add_argument(
        "--output", "-o", type=str,
        help=("HTML file with map of media file geocoordinates. Default: media_gpsplot.html"),
        default="media_gpsplot.html"
    )
    args = parser.parse_args()
    logger.debug('args: %s', args)

    # Get media file paths
    media_paths = args.media_path.split(",")
    media_paths = [Path(media_path) for media_path in media_paths]
    media_paths = [media_path.resolve() for media_path in media_paths]
    media_paths = [media_path for media_path in media_paths if media_path.is_dir()]
    print(f"Media paths: {media_paths}")
    logger.debug('Media paths: %s', media_paths)

    if len(media_paths) == 0:
        print("No valid media paths given. Exiting.")
        logger.debug('No valid media paths given. Exiting.')
        exit()

    # Media files to look for
    media_file_extensions = ["jpg", "jpeg", "heic", "mp4", "xml", "MTS"]
    logger.debug('media_file_extensions: %s', media_file_extensions)

    # Get media files
    media_files = []
    for media_path in media_paths:
        for media_file_extension in media_file_extensions:
            media_files.extend(media_path.glob(f"**/*.{media_file_extension}"))
            media_files.extend(media_path.glob(f"**/*.{media_file_extension.upper()}"))

    media_files = [media_file for media_file in media_files if media_file.is_file()]
    print(f"Media files: {media_files}")
    logger.debug('media_files: %s', media_files)
    heic_geocoord_df = get_coordinates_from_media_files(media_files, "heic", logger)
    print(f"HEIC geocoordinates dataframe: {heic_geocoord_df}")
    xml_geocoord_df = get_coordinates_from_media_files(media_files, "xml", logger)
    print(f"XML geocoordinates dataframe: {xml_geocoord_df}")
    media_geocoord_df = pd.concat([heic_geocoord_df, xml_geocoord_df])
    jpeg_geocoord_df = get_coordinates_from_media_files(media_files, "jpg", logger)
    print(f"JPEG geocoordinates dataframe: {jpeg_geocoord_df}")
    media_geocoord_df = pd.concat([media_geocoord_df, jpeg_geocoord_df])

    plot_map(media_geocoord_df, args.output, logger)

if __name__ == "__main__":
    main()
