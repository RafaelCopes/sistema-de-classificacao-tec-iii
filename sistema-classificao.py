import pandas as pd
import os
import requests
import re

# Classe Student
class Student:
    def __init__(self, name_attribute, **kwargs):
        self.name_attribute = name_attribute
        for key, value in kwargs.items():
            setattr(self, key, value)

    # Obtém o nome do aluno com base no atributo name.
    def get_name(self):
        return getattr(self, self.name_attribute, 'Unknown')

    # Verifica se o valor fornecido é um URL.
    def is_link(self, value):
        return isinstance(value, str) and value.startswith(("http://", "https://"))

    # Faz o download de todos os arquivos dos atributos URL e os salva na pasta com o nome do aluno.
    def download_files(self, downloader):
        folder_name = self.get_name()
        for attribute, value in vars(self).items():
            if self.is_link(value):
                downloader.download_file(attribute, value, folder_name)

# Classe FileDownloader
class FileDownloader:
    # Faz o download de um arquivo de uma URL e o salva na pasta especificada.
    def download_file(self, attribute, url, folder_name):
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

    # Obtém o token de confirmação para download do Google Drive.
    def get_confirm_token(self, response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    # Converte um link compartilhado do Google Drive em um link de download direto.
    def get_direct_google_drive_link(self, url):
        file_id = url.split('/')[-2]
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    # Remove caracteres inválidos e limita o comprimento do nome do arquivo.
    @staticmethod
    def sanitize_filename(filename):
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        return filename[:100]

# Classe CSVReader
class CSVReader:
    # Lê um arquivo CSV em um DataFrame do pandas.
    @staticmethod
    def read_csv_to_dataframe(file_path):
        if not os.path.isfile(file_path):
            print(f"File not found: {file_path}")
            return None
        try:
            dataframe = pd.read_csv(file_path)
            return dataframe
        except Exception as e:
            print(f"An error occurred while reading the CSV file: {e}")
            return None
        
# Classe StudentFactory usando o padrão Factory Method que é responsável por criar objetos Student.
class StudentFactory:
    # Cria uma lista de objetos Student a partir de um DataFrame do pandas.
    @staticmethod
    def create_students_from_dataframe(dataframe, name_attribute):
        if dataframe is None:
            print("DataFrame is None, cannot create students.")
            return []
        
        students = []
        for _, row in dataframe.iterrows():
            student = Student(name_attribute=name_attribute, **row.to_dict())
            students.append(student)
        return students


# Função principal
def main():
    file_path = 'inscricoes.csv'
    name_attribute = 'Nome Completo'
    
    df = CSVReader.read_csv_to_dataframe(file_path)
    if df is not None:
        students = StudentFactory.create_students_from_dataframe(df, name_attribute)
        downloader = FileDownloader()
        for student in students:
            student.download_files(downloader)

if __name__ == "__main__":
    main()
