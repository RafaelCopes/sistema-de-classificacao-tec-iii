import pandas as pd
import os
import requests
import re

# Classe Student
class Student:
    def __init__(self, name_attribute, **kwargs):
        self.name_attribute = name_attribute
        self.average_score = 0
        self.publication_scores = []
        self.publication_total_score = 0
        self.final_score = 0
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_name(self):
        return getattr(self, self.name_attribute, 'Unknown')

    def is_link(self, value):
        return isinstance(value, str) and value.startswith(("http://", "https://"))

    def download_files(self, downloader):
        folder_name = self.get_name()
        for attribute, value in vars(self).items():
            if self.is_link(value):
                downloader.download_file(attribute, value, folder_name)

    # Calcular pontuação média
    def calculate_average_score(self, average, course_type):
        try:
            average = float(average)
        except ValueError:
            self.average_score = 0
            return
        # Se curso tecnólogo, a pontuação média é 2.0
        if course_type.lower() == 'tecnólogo':
            self.average_score = 2.0
        else:
            # Se média for menor ou igual a 5.0, a pontuação média é 0.0
            if average <= 5.0:
                self.average_score = 0.0
            else:
                self.average_score = average - 5.0

    # Calcular pontuação das publicações
    def calculate_publication_scores(self):
        # Valores qualis
        qualis_points = {
            "A1": 5.00, "A2": 4.38, "A3": 3.75, "A4": 3.13,
            "B1": 2.50, "B2": 1.00, "B3": 0.50, "B4": 0.25, "sem qualis": 0.20
        }

        # 3 para mestrado
        publications = [
            {'qualis': getattr(self, 'Qualis do local de publicação', ''), 'first_author': getattr(self, 'Primeiro autor', '') == 'Sim'},
            {'qualis': getattr(self, 'Qualis do local de publicação.1', ''), 'first_author': getattr(self, 'Primeiro autor.1', '') == 'Sim'},
            {'qualis': getattr(self, 'Qualis do local de publicação.2', ''), 'first_author': getattr(self, 'Primeiro autor.2', '') == 'Sim'}
        ]

        # Calcular pontuação das publicações
        for pub in publications:
            if pub['qualis']: 
                score = qualis_points.get(pub['qualis'], 0)
                # Se não for primeiro autor, a pontuação é dividida por 3
                if not pub['first_author']:
                    score /= 3
                self.publication_scores.append(score)
        # Calcular pontuação total das publicações        
        if self.publication_scores:
            self.publication_total_score = sum(self.publication_scores) / len(self.publication_scores)
        else:
            self.publication_total_score = 0

    # Calcular nota final
    def calculate_final_score(self):
        # Nota final é a média entre a pontuação média e a pontuação total das publicações
        self.final_score = round((self.average_score + self.publication_total_score) / 2, 2)

    def print_scores(self):
        print(f"Nome: {self.get_name()}")
        print(f"  Pontuação Média: {self.average_score:.2f}")
        for i, score in enumerate(self.publication_scores):
            print(f"  Nota da Publicação {i + 1}: {score:.2f}")
        print(f"  Nota Final das Publicações: {self.publication_total_score:.2f}")
        print(f"  Nota Final: {self.final_score:.2f}")

    def get_publication_scores(self):
        return [f"Nota da Publicação {i + 1}: {score:.2f}" for i, score in enumerate(self.publication_scores)]

# Classe FileDownloader
class FileDownloader:
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

    def get_confirm_token(self, response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def get_direct_google_drive_link(self, url):
        file_id = url.split('/')[-2]
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    @staticmethod
    def sanitize_filename(filename):
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        return filename[:100]

# Classe CSVReader
class CSVReader:
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

# Processa os alunos, calcula as pontuações
def process_students(inscricoes_df, historico_df, name_attribute):
    if 'Tipo de inscrição' not in inscricoes_df.columns:
        raise KeyError("'Tipo de inscrição' column not found in inscricoes_df")
    
    if 'Tipo de curso' not in inscricoes_df.columns:
        raise KeyError("'Tipo de curso' column not found in inscricoes_df")

    # Selecionar alunos de mestrado
    mestrado_df = inscricoes_df[inscricoes_df['Tipo de inscrição'].str.lower() == 'mestrado']
    
    students = StudentFactory.create_students_from_dataframe(mestrado_df, name_attribute)
    downloader = FileDownloader()
    
    for student in students:
        # Obter tipo de curso
        inscricao = inscricoes_df[inscricoes_df['CPF'] == student.CPF]
        course_type = inscricao.iloc[0]['Tipo de curso']
        
        # Obter média do histórico
        historico = historico_df[historico_df['CPF'] == student.CPF]
        if not historico.empty:
            average = historico.iloc[0]['Media Historico']
            student.calculate_average_score(average, course_type)
        # Calcular pontuação das publicações
        student.calculate_publication_scores()
        student.calculate_final_score()
    
    return students

# Salva os resultados em um arquivo CSV
def save_results(students, output_file):
    # Criar DataFrame com resultados
    results = []
    for student in students:
        result = {
            'Nome': student.get_name(),
            'CPF': student.CPF,
            'Pontuacao Histórico': f"{student.average_score:.2f}",
        }
        for i, score in enumerate(student.publication_scores):
            result[f'Nota da Publicação {i + 1}'] = f"{score:.2f}"
        results.append(result)

        result['Nota Final Publicações'] = f"{student.publication_total_score:.2f}"
        result['Nota Final'] = f"{student.final_score:.2f}"
    
    results_df = pd.DataFrame(results)
    results_df = results_df[results_df['Nota Final'] >= '1.50']
    results_df.sort_values(by='Nota Final', ascending=False, inplace=True)
    
    results_df.to_csv(output_file, index=False)
    print(f"Resultados salvos em '{output_file}'")

def print_student_scores(students):
    for student in students:
        student.print_scores()

# Função principal
def main():
    inscricoes_path = 'inscricoes.csv'
    historico_path = 'historico.csv'
    name_attribute = 'Nome Completo'
    
    inscricoes_df = CSVReader.read_csv_to_dataframe(inscricoes_path)
    historico_df = CSVReader.read_csv_to_dataframe(historico_path)
    
    if inscricoes_df is not None and historico_df is not None:
        students = process_students(inscricoes_df, historico_df, name_attribute)
        save_results(students, 'resultados_mestrado.csv')
        print_student_scores(students)

if __name__ == "__main__":
    main()
