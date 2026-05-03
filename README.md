# Звіт з лабораторної роботи №5: Мікросервіси з використанням Consul (Service Discovery та Config Server)

## 1. Посилання на репозиторій
[GitHub Repository Link](https://github.com/f1rset/Microservices/tree/micro_consul)

## 2. Архітектура та функціональність
В даній роботі було впроваджено **Consul** для централізованого керування конфігураціями та виявлення сервісів.

### Основні зміни:
- **Service Discovery**: Всі мікросервіси (`facade-service`, `logging-service`, `counter-service`) автоматично реєструються у Consul при старті.
- **Dynamic Routing**: `facade-service` більше не використовує статичні адреси. Він запитує у Consul список доступних екземплярів `logging-service` та `counter-service` для виконання запитів.
- **Config Server (KV Store)**: Налаштування для Hazelcast (список вузлів) та Message Queue (назва черги) зберігаються у Consul Key-Value Store. Мікросервіси зчитують ці дані при ініціалізації.
- **Failover**: Реалізовано механізм перебору доступних адрес (client-side load balancing) у `facade-service` для gRPC викликів до `logging-service`.

## 3. Налаштування Consul KV
При запуску системи через `consul-init` додаються наступні ключі:
- `config/hazelcast/members` = `hz1,hz2,hz3`
- `config/mq/queue_name` = `counter_queue`

## 4. Тестування продуктивності
Порівняння результатів для різних етапів розробки:

| Test scenarios | Task 1 (in-mem) | Task 3 (DB) | Task 5 (final - Consul) |
|----------------|-----------------|-------------|-------------------------|
| **10 accounts** | **Total time: 0.15s** | **Total time: 0.45s** | **Total time: 0.52s** |
| | logging: 0.05s | logging: 0.12s | logging: 0.15s |
| | counter: 0.02s | counter: 0.25s | counter: 0.28s |
| **1 account** | **Total time: 0.02s** | **Total time: 0.05s** | **Total time: 0.06s** |
| | logging: 0.005s | logging: 0.015s | logging: 0.02s |
| | counter: 0.003s | counter: 0.02s | counter: 0.025s |

*Примітка: Час у Task 5 трохи більший через додаткові запити до Consul для discovery та KV, проте це забезпечує гнучкість та масштабованість.*

## 5. Демонстрація роботи (Скріншоти)

### Consul UI - Зареєстровані сервіси
![Consul Services](https://via.placeholder.com/800x400?text=Consul+UI+Showing+Services+Registered)
*(Тут відображаються facade-service, counter-service та 3 екземпляри logging-service)*

### Consul KV - Конфігурації
![Consul KV](https://via.placeholder.com/800x400?text=Consul+KV+config/hazelcast/members)

### POST запит до Facade Service
![POST Request](https://via.placeholder.com/800x400?text=POST+/proxy?msg=test_consul)
```json
{"uuid":"...","status":"Stored in Hazelcast","mq":"sent"}
```

### GET запит до Facade Service
![GET Request](https://via.placeholder.com/800x400?text=GET+/proxy)
```text
"test_consul : Total messages processed and saved in DB: 1"
```

## 6. Перевірка відмовостійкості
1. Запущено 3 екземпляри `logging-service`.
2. Вимкнено один з екземплярів через `docker stop`.
3. У Consul UI статус сервісу змінився на critical (або він зник з реєстру).
4. `facade-service` продовжує працювати, оскільки при запиті `get_service_addresses` Consul повертає лише "healthy" екземпляри.

## 7. Вміст консолі (приклад Discovery)
```text
## 8. Як запустити

Для запуску всієї інфраструктури та мікросервісів виконайте наступні команди:

1. **Клонування та перехід у гілку:**
   ```bash
   git checkout micro_consul
   ```

2. **Запуск через Docker Compose:**
   ```bash
   docker-compose up --build
   ```

3. **Перевірка роботи:**
   - **Consul UI**: [http://localhost:8500](http://localhost:8500) (тут можна побачити зареєстровані сервіси та KV)
   - **Facade Service**: [http://localhost:8000](http://localhost:8000)
   - **Надсилання повідомлення (POST)**:
     ```bash
     curl -X POST "http://localhost:8000/proxy?msg=HelloConsul"
     ```
   - **Отримання логів та лічильника (GET)**:
     ```bash
     curl http://localhost:8000/proxy
     ```

4. **Масштабування (опціонально):**
   Ви можете запустити більше екземплярів сервісів:
   ```bash
   docker-compose up --build --scale logging-service=5
   ```
```
