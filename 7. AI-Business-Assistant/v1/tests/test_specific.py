import requests

def test_chat(query: str):
    print(f"\n==================================================")
    print(f"Query: {query}")
    print(f"--------------------------------------------------")
    
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={"query": query},
            timeout=60
        )
        if response.status_code == 200:
            print(response.json()["response"])
        else:
            print(f"API returned {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error connecting to API: {e}")

if __name__ == "__main__":
    test_chat("Doanh thu bán hàng và cung cấp dịch vụ tháng 7/2026 là bao nhiêu?")
    test_chat("Tổng giá trị tồn kho của kho HÀNG HÓA là bao nhiêu?")
