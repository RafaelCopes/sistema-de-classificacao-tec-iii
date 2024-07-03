import pandas as pd
import os
import requests
import re

class Student:
    def __init__(self, name_attribute, **kwargs):
        self.name_attribute = name_attribute
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_name(self):
        """
        Gets the student's name based on the name attribute.
        """
        return getattr(self, self.name_attribute, 'Unknown')

    def is_link(self, value):
        """
        Checks if the given value is a URL.
        """
        return isinstance(value, str) and value.startswith(("http://", "https://"))

    def download_files(self, downloader):
        """
        Downloads all files from URL attributes and saves them in the folder named after the student.
        """
        folder_name = self.get_name()
        for attribute, value in vars(self).items():
            if self.is_link(value):
                downloader.download_file(attribute, value, folder_name)


class FileDownloader:
    def download_file(self, attribute, url, folder_name):
        """
        Downloads a file from a URL and saves it in the specified folder.
        
        Parameters:
        attribute (str): The attribute name that contains the URL.
        url (str): The URL of the file to be downloaded.
        folder_name (str): The name of the folder to save the file in.
        """
        if 'drive.google.com' in url:
            url = self.get_direct_google_drive_link(url)
        
        session = requests.Session()
        response = session.get(url, stream=True)
        token = self.get_confirm_token(response)

        if token:
            url = url + "&confirm=" + token
            response = session.get(url, stream=True)

        if response.status_code == 200:
            os.makedirs(folder_name, exist_ok=True)
            file_name = os.path.join(folder_name, self.sanitize_filename(f"{attribute}.pdf"))
            with open(file_name, 'wb') as file:
                for chunk in response.iter_content(chunk_size=32768):
                    if chunk:
                        file.write(chunk)
            print(f"Downloaded {file_name}")
        else:
            print(f"Failed to download file from {url}")

    def get_confirm_token(self, response):
        """
        Get confirmation token for Google Drive download.
        
        Parameters:
        response (requests.Response): The initial response from Google Drive.
        
        Returns:
        str: The confirmation token if present, else None.
        """
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def get_direct_google_drive_link(self, url):
        """
        Converts a Google Drive shareable link to a direct download link.
        
        Parameters:
        url (str): The Google Drive shareable link.
        
        Returns:
        str: The direct download link.
        """
        file_id = url.split('/')[-2]
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    @staticmethod
    def sanitize_filename(filename):
        """
        Sanitize the filename to remove or replace invalid characters and limit its length.
        
        Parameters:
        filename (str): The original filename.
        
        Returns:
        str: The sanitized filename.
        """
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Limit the length of the filename
        return filename[:100]


class CSVReader:
    @staticmethod
    def read_csv_to_dataframe(file_path):
        """
        Reads a CSV file into a pandas DataFrame.
        
        Parameters:
        file_path (str): The path to the CSV file.
        
        Returns:
        pandas.DataFrame: The DataFrame containing the CSV data, or None if the file does not exist.
        """
        if not os.path.isfile(file_path):
            print(f"File not found: {file_path}")
            return None
        try:
            dataframe = pd.read_csv(file_path)
            return dataframe
        except Exception as e:
            print(f"An error occurred while reading the CSV file: {e}")
            return None


class StudentFactory:
    @staticmethod
    def create_students_from_dataframe(dataframe, name_attribute):
        """
        Creates a list of Student objects from a pandas DataFrame.
        
        Parameters:
        dataframe (pandas.DataFrame): The DataFrame containing student data.
        name_attribute (str): The column name that represents the student's name.
        
        Returns:
        list: A list of Student objects.
        """
        if dataframe is None:
            print("DataFrame is None, cannot create students.")
            return []
        
        students = []
        for _, row in dataframe.iterrows():
            student = Student(name_attribute=name_attribute, **row.to_dict())
            students.append(student)
        return students


# Example usage
def main():
    file_path = 'inscricoes.csv'  # Replace with the correct path to your CSV file
    name_attribute = 'Nome Completo'  # Replace with the actual column name representing the student's name
    
    df = CSVReader.read_csv_to_dataframe(file_path)
    if df is not None:
        students = StudentFactory.create_students_from_dataframe(df, name_attribute)
        downloader = FileDownloader()
        for student in students:
            student.download_files(downloader)

if __name__ == "__main__":
    main()
