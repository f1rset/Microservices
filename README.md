# Microservices

```
https://github.com/f1rset/Microservices
```
Inside repository just run:
```bash
docker compose up (-d for silent)
```

1. Services Running
![alt text](images/image.png)
2. Messages can be read
![alt text](images/image-3.png)
3. Kill one logging service
![alt text](images/image-2.png)
![alt text](images/image-1.png)
No data impact
![alt text](images/image-4.png)
4. Kill two hazelcast nodes (huge data loss because of no time to move data)
![alt text](images/image-6.png)
![alt text](images/image-5.png)