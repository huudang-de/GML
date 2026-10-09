from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

class RAGAgent:
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        self.vectorstore = self._load_or_build_vectorstore()

    def _load_or_build_vectorstore(self):
        db_path = "./chroma_db"
        try:
            if os.path.exists(db_path):
                return Chroma(persist_directory=db_path, embedding_function=self.embeddings)
            else:
                return self._build_vectorstore()
        except:
            return self._build_vectorstore()

    def _build_vectorstore(self):
        # We will adjust this script later when we actually build the index.
        # For now we provide a fallback empty vector store if building fails.
        try:
            loader = DirectoryLoader(r"D:\Công việc\1. Dự án Gỗ Minh Long\4. Phát triển báo cáo", glob="guide_dashboard*.md",
                                      loader_cls=UnstructuredMarkdownLoader)
            docs = loader.load()

            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = splitter.split_documents(docs)

            vectorstore = Chroma.from_documents(
                chunks, self.embeddings, persist_directory="./chroma_db"
            )
            return vectorstore
        except Exception as e:
            # Return an empty initialized vector store
            return Chroma(persist_directory="./chroma_db", embedding_function=self.embeddings)

    def run(self, state: dict) -> dict:
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        relevant_docs = retriever.get_relevant_documents(state["query"])
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        sources = [doc.metadata.get("source", "Unknown") for doc in relevant_docs]

        return {**state, "rag_context": context, "sources": sources}
