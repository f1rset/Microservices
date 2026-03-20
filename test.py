for i in {1..10}; do 
  curl -X POST "http://localhost:8000/proxy?msg=msg$i"
  echo -e "\n"
done
