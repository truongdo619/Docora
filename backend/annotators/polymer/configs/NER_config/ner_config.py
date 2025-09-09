from pycorenlp import StanfordCoreNLP

# Configuration settings
DEBUG = False
CORENLP_SERVER_ADDRESS = 'http://localhost:9000'
UPLOAD_DIR = "uploads"
nlp = StanfordCoreNLP(CORENLP_SERVER_ADDRESS)
