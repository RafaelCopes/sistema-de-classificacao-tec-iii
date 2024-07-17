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
        self.project_score = 0
        self.memorial_score = 0
        self.interview_score = 0
        self.final_doctorate_score = 0
        self.inscricao_type = kwargs.get('Tipo de inscrição', '').lower()
        
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

        # Determinar o número de publicações a considerar
        if self.inscricao_type == 'mestrado':
            num_publications = 3
        elif self.inscricao_type == 'doutorado':
            num_publications = 5
        else:
            num_publications = 0

        publications = []

        # Adicionar a primeira publicação sem sufixo numérico
        publications.append({
            'qualis': getattr(self, 'Qualis do local de publicação', ''),
            'first_author': getattr(self, 'Primeiro autor', '') == 'Sim'
        })

        # Adicionar as demais publicações com sufixo numérico
        for i in range(1, num_publications):
            publications.append({
                'qualis': getattr(self, f'Qualis do local de publicação.{i}', ''),
                'first_author': getattr(self, f'Primeiro autor.{i}', '') == 'Sim'
            })

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

    # Calcular pontuação do projeto, memorial e entrevista
    def calculate_doctorate_scores(self, project_scores, memorial_scores, interview_scores):
        self.project_score = sum(project_scores) / len(project_scores)
        self.memorial_score = sum(memorial_scores) / len(memorial_scores)
        self.interview_score = sum(interview_scores) / len(interview_scores)
        self.final_doctorate_score = (self.project_score + self.memorial_score + self.interview_score) / 3

    # Calcular nota final
    def calculate_final_score(self):
        # Se mestrado, a nota final é a média entre a pontuação média e a pontuação total das publicações
        if self.inscricao_type == 'mestrado':
            self.final_score = round((self.average_score + self.publication_total_score) / 2, 2)
        
        # Se doutorado, a nota final é a média ponderada entre a pontuação média, pontuação total das publicações e a pontuação final do doutorado
        if self.inscricao_type == 'doutorado':
            self.final_score = round((
                (self.average_score * 2) + 
                (self.publication_total_score * 5) + 
                (self.final_doctorate_score * 3)
            ) / 10, 2)

    def print_scores(self):
        print(f"Nome: {self.get_name()}")
        print(f"  Pontuação Média: {self.average_score:.2f}")
        for i, score in enumerate(self.publication_scores):
            print(f"  Nota da Publicação {i + 1}: {score:.2f}")
        print(f"  Nota Final das Publicações: {self.publication_total_score:.2f}")
        if self.inscricao_type == 'doutorado':
            print(f"  Projeto de Doutorado: {self.project_score:.2f}")
            print(f"  Memorial Acadêmico: {self.memorial_score:.2f}")
            print(f"  Entrevista: {self.interview_score:.2f}")
        
        print(f"  Nota Final: {self.final_score:.2f}")
        print("\n")

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

def get_masters_scores(student, inscricoes_df, historico_df):
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

def get_doctorate_scores(student, inscricoes_df, historico_df, avaliacoes_df):
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
    
    # Obter notas de projeto, memorial e entrevista
    avaliacoes = avaliacoes_df[avaliacoes_df['CPF'] == student.CPF]
    if not avaliacoes.empty:
        project_scores = avaliacoes[['Nota projeto 1', 'Nota projeto 2', 'Nota projeto 3']].values.flatten().tolist()
        memorial_scores = avaliacoes[['Nota memorial 1', 'Nota memorial 2', 'Nota memorial 3']].values.flatten().tolist()
        interview_scores = avaliacoes[['Nota entrevista 1', 'Nota entrevista 2', 'Nota entrevista 3']].values.flatten().tolist()
        student.calculate_doctorate_scores(project_scores, memorial_scores, interview_scores)
    
    student.calculate_final_score()

# Processa os alunos, calcula as pontuações
def process_students(inscricoes_df, historico_df, avaliacoes_df, name_attribute):
    if 'Tipo de inscrição' not in inscricoes_df.columns:
        raise KeyError("'Tipo de inscrição' column not found in inscricoes_df")
    
    if 'Tipo de curso' not in inscricoes_df.columns:
        raise KeyError("'Tipo de curso' column not found in inscricoes_df")

    # Selecionar alunos de mestrado e doutorado
    mestrado_df = inscricoes_df[inscricoes_df['Tipo de inscrição'].str.lower() == 'mestrado']
    doutorado_df = inscricoes_df[inscricoes_df['Tipo de inscrição'].str.lower() == 'doutorado']
    
    students_mestrado = StudentFactory.create_students_from_dataframe(mestrado_df, name_attribute)
    students_doutorado = StudentFactory.create_students_from_dataframe(doutorado_df, name_attribute)
    downloader = FileDownloader()

    for student in students_mestrado:
        get_masters_scores(student, inscricoes_df, historico_df)

    for student in students_doutorado:
        get_doctorate_scores(student, inscricoes_df, historico_df, avaliacoes_df)

    return students_mestrado, students_doutorado

# Salva os resultados em arquivos CSV
def save_results(students_mestrado, students_doutorado, output_file_mestrado, output_file_doutorado):
    # Criar DataFrame com resultados dos alunos de mestrado
    results_mestrado = []
    for student in students_mestrado:
        result = {
            'Nome': student.get_name(),
            'CPF': student.CPF,
            'Pontuacao Histórico': f"{student.average_score:.2f}",
        }
        for i, score in enumerate(student.publication_scores):
            result[f'Nota da Publicação {i + 1}'] = f"{score:.2f}"
        results_mestrado.append(result)

        result['Nota Final Publicações'] = f"{student.publication_total_score:.2f}"
        result['Nota Final'] = f"{student.final_score:.2f}"
    
    results_mestrado_df = pd.DataFrame(results_mestrado)
    results_mestrado_df = results_mestrado_df[results_mestrado_df['Nota Final'].astype(float) >= 1.50]
    results_mestrado_df.sort_values(by='Nota Final', ascending=False, inplace=True)
    results_mestrado_df.to_csv(output_file_mestrado, index=False)
    print(f"Resultados de mestrado salvos em '{output_file_mestrado}'")

    # Criar DataFrame com resultados dos alunos de doutorado
    results_doutorado = []
    for student in students_doutorado:
        result = {
            'Nome': student.get_name(),
            'CPF': student.CPF,
            'Pontuacao Histórico': f"{student.average_score:.2f}",
            'Projeto de Doutorado': f"{student.project_score:.2f}",
            'Memorial Acadêmico': f"{student.memorial_score:.2f}",
            'Entrevista': f"{student.interview_score:.2f}"
        }
        for i, score in enumerate(student.publication_scores):
            result[f'Nota da Publicação {i + 1}'] = f"{score:.2f}"
        results_doutorado.append(result)

        result['Nota Final Publicações'] = f"{student.publication_total_score:.2f}"
        result['Nota Final'] = f"{student.final_score:.2f}"
    
    results_doutorado_df = pd.DataFrame(results_doutorado)
    results_doutorado_df = results_doutorado_df[results_doutorado_df['Nota Final'].astype(float) >= 1.50]
    results_doutorado_df.sort_values(by='Nota Final', ascending=False, inplace=True)
    results_doutorado_df.to_csv(output_file_doutorado, index=False)
    print(f"Resultados de doutorado salvos em '{output_file_doutorado}'")

def print_student_scores(students):
    for student in students:
        student.print_scores()

# Função principal
def main():
    inscricoes_path = 'inscricoes.csv'
    historico_path = 'historico.csv'
    avaliacoes_path = 'avaliacoes.csv'
    name_attribute = 'Nome Completo'
    
    inscricoes_df = CSVReader.read_csv_to_dataframe(inscricoes_path)
    historico_df = CSVReader.read_csv_to_dataframe(historico_path)
    avaliacoes_df = CSVReader.read_csv_to_dataframe(avaliacoes_path)
    
    if inscricoes_df is not None and historico_df is not None and avaliacoes_df is not None:
        students_mestrado, students_doutorado = process_students(inscricoes_df, historico_df, avaliacoes_df, name_attribute)
        save_results(students_mestrado, students_doutorado, 'resultados_mestrado.csv', 'resultados_doutorado.csv')
        #print_student_scores(students_mestrado + students_doutorado)

if __name__ == "__main__":
    main()
