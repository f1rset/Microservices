# Звіт з лабораторної роботи №4: Мікросервіси з використанням Message Queue

## 1. Посилання на репозиторій
[GitHub Repository Link](https://github.com/f1rset/Microservices)

## 2. Архітектура та функціональність
Система складається з таких мікросервісів:
- **Facade Service**: Приймає HTTP POST та GET запити. POST-запити перенаправляються в чергу `counter_queue` через Hazelcast та логуються через gRPC.
- **Logging Service**: 3 екземпляри, що зберігають логи в Hazelcast Distributed Map.
- **Counter Service**: Зчитує повідомлення з черги `counter_queue` (consumer) та зберігає їх у базу даних PostgreSQL.
- **Config Server**: Сервіс виявлення, де реєструються інші мікросервіси при старті.

## 3. Результати тестування (POST та GET запити)

**Відправка 10 POST-транзакцій (`msg1`-`msg10`):**
```json
{"uuid":"454e478e-82dc-44cb-8e4f-c1da37b1f8ab","status":"Stored in Hazelcast","mq":"sent"}
{"uuid":"c97dd86b-dadd-43f3-af81-8ca4c445f679","status":"Stored in Hazelcast","mq":"sent"}
{"uuid":"29980535-38cc-4e7a-9c46-66cba6338920","status":"Stored in Hazelcast","mq":"sent"}
{"uuid":"00b36997-5882-435c-b090-f07f0bb28ae0","status":"Stored in Hazelcast","mq":"sent"}
{"uuid":"ff85bc3b-c8db-43f9-bce5-6eb72fde516f","status":"Stored in Hazelcast","mq":"sent"}
{"uuid":"40f31c3f-b85e-4a75-8641-c3f88ac5fd10","status":"Stored in Hazelcast","mq":"sent"}
{"uuid":"79c5ca29-8e1b-41d0-a4e4-c33f0b73d798","status":"Stored in Hazelcast","mq":"sent"}
{"uuid":"5e53b1ee-0b35-4fe2-99b5-b8e71d5e5baa","status":"Stored in Hazelcast","mq":"sent"}
{"uuid":"4bdb1fee-a876-4c95-a40a-3dfaf9cc3512","status":"Stored in Hazelcast","mq":"sent"}
{"uuid":"8627069d-68b1-46da-b3c0-ef739cdce540","status":"Stored in Hazelcast","mq":"sent"}
```

**Перевірка через GET-запит:**
```text
"msg3, msg6, msg4, msg9, msg1, msg10, msg2, msg7, msg5, msg8 : \"Total messages processed and saved in DB: 17\""
```
*(Лічильник дорівнює 17, оскільки тестова база містила 7 старих записів)*

## 4. Перевірка відмовостійкості

1. **Зупинка споживача**: Виконано `docker pause microservices-counter-service-1`.
2. **Відправка нових транзакцій**: Було відправлено ще 5 POST-запитів (`msg11`-`msg15`). Фасад-сервіс успішно відправив їх до Message Queue без помилок.
3. **Перевірка стану (GET)**: Оскільки `counter-service` недоступний, фасад повернув помилку з'єднання для лічильника, але вивів логи:
   ```text
   "msg3, msg6, msg11, msg4, msg13, msg9, msg12, msg1, msg14, msg10, msg2, msg7, msg15, msg5, msg8 : [Counter-service Error]"
   ```
4. **Відновлення**: Після виконання `docker unpause microservices-counter-service-1` сервіс відразу вичитав накопичені повідомлення з черги, і наступний GET-запит показав коректне значення:
   ```text
   "msg3, msg6, msg11, msg4, msg13, msg9, msg12, msg1, msg14, msg10, msg2, msg7, msg15, msg5, msg8 : \"Total messages processed and saved in DB: 22\""
   ```

## 5. Вміст консолі мікросервісів

### Logging Service 1
```text
INFO:logging-service: [gRPC] Received and stored: 29980535-38cc-4e7a-9c46-66cba6338920 -> msg3
INFO:logging-service: [gRPC] Received and stored: ff85bc3b-c8db-43f9-bce5-6eb72fde516f -> msg5
INFO:logging-service: [gRPC] Received and stored: 40f31c3f-b85e-4a75-8641-c3f88ac5fd10 -> msg6
INFO:logging-service: [gRPC] Received and stored: 5e53b1ee-0b35-4fe2-99b5-b8e71d5e5baa -> msg8
INFO:logging-service: [gRPC] Received and stored: c097d492-d4fa-4de8-bfe0-391469e9a7f2 -> msg12
INFO:logging-service: [gRPC] Returning all logs. Count: 15
```

### Logging Service 2
```text
INFO:logging-service: [gRPC] Received and stored: c97dd86b-dadd-43f3-af81-8ca4c445f679 -> msg2
INFO:logging-service: [gRPC] Received and stored: 00b36997-5882-435c-b090-f07f0bb28ae0 -> msg4
INFO:logging-service: [gRPC] Received and stored: 79c5ca29-8e1b-41d0-a4e4-c33f0b73d798 -> msg7
INFO:logging-service: [gRPC] Received and stored: 8872f6bc-2a95-4e53-b5f7-3982dda98495 -> msg13
INFO:logging-service: [gRPC] Received and stored: f64d4d5e-a14c-4582-b3ee-4b918a4c59f5 -> msg14
INFO:logging-service: [gRPC] Received and stored: 902224db-338d-470e-803e-4538fca305f5 -> msg15
INFO:logging-service: [gRPC] Returning all logs. Count: 15
```

### Logging Service 3
```text
INFO:logging-service: [gRPC] Received and stored: 454e478e-82dc-44cb-8e4f-c1da37b1f8ab -> msg1
INFO:logging-service: [gRPC] Received and stored: 4bdb1fee-a876-4c95-a40a-3dfaf9cc3512 -> msg9
INFO:logging-service: [gRPC] Received and stored: 8627069d-68b1-46da-b3c0-ef739cdce540 -> msg10
INFO:logging-service: [gRPC] Received and stored: 731071e6-6237-479e-9b93-a1535cb59b79 -> msg11
INFO:logging-service: [gRPC] Returning all logs. Count: 15
```

### Counter Service
```text
INFO:counter-service:Received message from MQ: msg8
INFO:counter-service:Updated counter to: 15
INFO:counter-service:Received message from MQ: msg9
INFO:counter-service:Updated counter to: 16
INFO:counter-service:Received message from MQ: msg10
INFO:counter-service:Updated counter to: 17
... (після паузи та відновлення)
INFO:counter-service:Received message from MQ: msg11
INFO:counter-service:Updated counter to: 18
INFO:counter-service:Received message from MQ: msg12
INFO:counter-service:Updated counter to: 19
INFO:counter-service:Received message from MQ: msg13
INFO:counter-service:Updated counter to: 20
INFO:counter-service:Received message from MQ: msg14
INFO:counter-service:Updated counter to: 21
INFO:counter-service:Received message from MQ: msg15
INFO:counter-service:Updated counter to: 22
```

### Facade Service
```text
INFO:facade-service:Message 'msg13' sent to counter_queue
INFO:     172.20.0.1:45332 - "POST /proxy?msg=msg13 HTTP/1.1" 200 OK
INFO:facade-service:Attempting to contact logging-service at d61ee84065e2:50051
INFO:facade-service:Message 'msg14' sent to counter_queue
INFO:     172.20.0.1:45346 - "POST /proxy?msg=msg14 HTTP/1.1" 200 OK
INFO:facade-service:Attempting to contact logging-service at d61ee84065e2:50051
INFO:facade-service:Message 'msg15' sent to counter_queue
INFO:     172.20.0.1:45354 - "POST /proxy?msg=msg15 HTTP/1.1" 200 OK
ERROR:facade-service:Counter-service error at http://e3c9f6f8dda2:8002/message:
```

