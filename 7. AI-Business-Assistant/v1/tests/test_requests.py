import sys; sys.stdout.reconfigure(encoding='utf-8')
import requests

url = 'http://localhost:8000/chat'

def test_query(test_name, query):
    print(f'\n==================================================')
    print(f'Test Case: {test_name}')
    print(f'Query: {query}')
    print(f'--------------------------------------------------')
    
    try:
        response = requests.post(url, json={'query': query})
        if response.status_code != 200:
            print(f'API returned {response.status_code}: {response.text}')
            return
            
        data = response.json()
        print(f'🧠 Intent Classified: {data.get("intent")}')
        
        if data.get('sql_query'):
            print('\n🔍 SQL Generated:')
            print(data.get('sql_query'))
            
        if data.get('sources'):
            print('\n📄 RAG Sources Found:')
            for src in data.get('sources'):
                print(f' - {src}')
                
        print('\n🤖 Final Answer:')
        print(data.get('answer'))
    except Exception as e:
        print('Error:', e)

test_query('SQL Agent', 'Lấy danh sách 3 khách hàng có dư nợ cao nhất?')
test_query('RAG Agent', 'Vòng quay phải thu được tính thế nào?')
test_query('Both', 'Tại sao lợi nhuận tháng 9 giảm?')
