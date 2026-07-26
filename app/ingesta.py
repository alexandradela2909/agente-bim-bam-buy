"""
Script de ingesta para el agente de BimBam Buy.

Genera el índice FAISS a partir de los documentos PDF.

Ejecutar:

    python app/ingesta.py
"""

from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

CARPETA_DOCUMENTOS = Path(__file__).parent.parent / "documentos"
CARPETA_INDICE = Path(__file__).parent.parent / "indice_faiss"

MODELO_EMBEDDINGS = "intfloat/multilingual-e5-small"


# --------------------------------------------------------
# Cargar PDFs
# --------------------------------------------------------

def cargar_pdfs(carpeta: Path):

    loader = DirectoryLoader(
        str(carpeta),
        glob="*.pdf",
        loader_cls=PyPDFLoader,
    )

    documentos = loader.load()

    for doc in documentos:

        nombre = Path(doc.metadata["source"]).name

        doc.metadata["archivo"] = nombre

        # Prefijo recomendado por E5
        doc.page_content = (
            f"passage: Documento: {Path(nombre).stem}\n\n"
            f"{doc.page_content}"
        )

    return documentos


# --------------------------------------------------------
# Trocear documentos
# --------------------------------------------------------

def trocear_documentos(documentos):

    splitter = RecursiveCharacterTextSplitter(

        chunk_size=1800,

        chunk_overlap=300,

        separators=[
            r"\n\d{1,2}\.\s+[A-ZÁÉÍÓÚÑ]",
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],

        is_separator_regex=True,
    )

    fragmentos = splitter.split_documents(documentos)

    return fragmentos


# --------------------------------------------------------
# Construir índice
# --------------------------------------------------------

def construir_indice(documentos):

    embeddings = HuggingFaceEmbeddings(
        model_name=MODELO_EMBEDDINGS
    )

    return FAISS.from_documents(
        documentos,
        embeddings,
    )


# --------------------------------------------------------
# Main
# --------------------------------------------------------

def main():

    if not CARPETA_DOCUMENTOS.exists():

        raise FileNotFoundError(
            f"No existe {CARPETA_DOCUMENTOS}"
        )

    if not any(CARPETA_DOCUMENTOS.glob("*.pdf")):

        raise FileNotFoundError(
            "No se encontraron documentos PDF."
        )

    documentos = cargar_pdfs(CARPETA_DOCUMENTOS)

    fragmentos = trocear_documentos(documentos)

    indice = construir_indice(fragmentos)

    indice.save_local(
        str(CARPETA_INDICE)
    )


if __name__ == "__main__":
    main()