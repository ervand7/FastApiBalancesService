#!/bin/bash

TESTNUM="$1"
USERID=$(uuidgen)
USERNAME="${TESTNUM}.boss"

curl -X POST 'http://localhost:8000/api/users/' \
     -H "Content-Type: application/json" \
     --data-binary "{\"id\":\"${USERID}\",\"name\":\"${USERNAME}\"}"
echo ""

transact() {
    tp="$1"
    number="$2"
    date="$3"
    amount="$4"
    TXID=$(uuidgen)
    curl -X POST 'http://localhost:8000/api/transactions/' \
         -H "Content-Type: application/json" \
         --data-binary "{\"id\": \"${TXID}\",\"user_id\":\"${USERID}\",\"amount\":\"${amount}\",\"created_at\":\"${date}T01:00:00\",\"type\":\"${tp}\"}"
    echo ""
}

transact DEPOSIT 0 2023-01-01 1000.0
transact DEPOSIT 1 2023-01-01 1000.0

curl "http://localhost:8000/api/users/${USERID}/balance/"
echo ""

transact DEPOSIT 2 2023-02-01 500.0

curl "http://localhost:8000/api/users/${USERID}/balance/"
echo ""

curl "http://localhost:8000/api/users/${USERID}/balance/?ts=2023-01-02"
echo ""

transact WITHDRAW 3 2023-03-01 700.0 &
transact WITHDRAW 4 2023-03-01 700.0 &
transact WITHDRAW 5 2023-03-01 700.0 &
transact WITHDRAW 6 2023-03-01 700.0 &
transact WITHDRAW 7 2023-03-01 700.0 &

sleep 2
echo ""

curl "http://localhost:8000/api/users/${USERID}/balance/"
echo ""
