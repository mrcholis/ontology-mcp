# 🎨 Ontology Mapping - Visual Guide

## **Complete Transformation Flow**

```
┌─────────────────────────────────────────────────────────────────────┐
│                     YOUR ISO 20022 XML                               │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FINANCIAL SIGNAL (Python)                         │
│  PaymentCancellationSignal(                                         │
│    amount=USD 125,000,                                              │
│    assignor=BLUEUSNY001,                                            │
│    assignee=GRENCHZZ002                                             │
│  )                                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  RDF TRIPLES (Semantic Web)                          │
│  :payment a fin:PaymentCancellation                                 │
│  :payment fin:hasAmount :amount                                     │
│  :payment fin:fromInstitution :bluebank                             │
│  :amount fin:value 125000                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## **Side-by-Side Comparison**

### **BEFORE (JSON - Just Data):**

```json
{
  "case_id": "20220718USDDSA9407803873BLUEUSNY001",
  "amount": {
    "value": 125000,
    "currency": "USD"
  },
  "assignor": {
    "bic": "BLUEUSNY001"
  },
  "assignee": {
    "bic": "GRENCHZZ002"
  },
  "cancellation_reason_code": "CUST"
}
```

**What machines understand:** "Some fields with values"
**What you can do:** Parse, filter, display
**Problem:** No semantic meaning, hard to query relationships

---

### **AFTER (RDF - Semantic Data):**

```turtle
inst:payment_cancellation_20220718USDDSA9407803873BLUEUSNY001
    a fin:PaymentCancellation, iso20022:camt_056 ;
    fin:caseId "20220718USDDSA9407803873BLUEUSNY001"^^xsd:string ;
    fin:hasAmount inst:amount_20220718USDDSA9407803873BLUEUSNY001 ;
    fin:fromInstitution inst:institution_BLUEUSNY001 ;
    fin:toInstitution inst:institution_GRENCHZZ002 ;
    fin:hasReason inst:reason_CUST ;
    fin:timestamp "2022-07-18T13:28:33"^^xsd:dateTime ;
    fin:confidence 1.0 .

inst:amount_20220718USDDSA9407803873BLUEUSNY001
    a fin:Amount ;
    fin:value 125000.0^^xsd:decimal ;
    fin:currency "USD"^^xsd:string .

inst:institution_BLUEUSNY001
    a fin:FinancialInstitution ;
    fin:bic "BLUEUSNY001"^^xsd:string .

inst:institution_GRENCHZZ002
    a fin:FinancialInstitution ;
    fin:bic "GRENCHZZ002"^^xsd:string .

inst:reason_CUST
    a fin:CancellationReason ;
    fin:reasonCode "CUST"^^xsd:string .

inst:transaction_455d2a5faecb4167ad8c1d985588e8e2
    a fin:Transaction ;
    fin:transactionId "455d2a5faecb4167ad8c1d985588e8e2"^^xsd:string ;
    fin:endToEndId "8f01d8db87fa4ef888e223a6f5eef3aa"^^xsd:string ;
    fin:messageId "20220718USDDSA9153934686BLUEUSNY001"^^xsd:string .
```

**What machines understand:** "This IS a payment cancellation. It HAS an amount. It's FROM an institution. These are RELATIONSHIPS."

**What you can do:**
- Query: "Show me all cancellations > $100k"
- Reason: "This bank has 5 cancellations in 1 hour → fraud alert"
- Link: Connect to other knowledge graphs
- Infer: Deduce patterns and relationships

---

## **The Power of Ontology**

### **Query Example 1: Find High-Value Cancellations**

```sparql
PREFIX fin: <http://example.org/financial/ontology#>

SELECT ?signal ?amount ?from ?to
WHERE {
    ?signal a fin:PaymentCancellation .
    ?signal fin:hasAmount ?amountObj .
    ?amountObj fin:value ?amount .
    FILTER(?amount > 100000)
    
    ?signal fin:fromInstitution ?fromInst .
    ?fromInst fin:bic ?from .
    ?signal fin:toInstitution ?toInst .
    ?toInst fin:bic ?to .
}
ORDER BY DESC(?amount)
```

**Results:**
```
Case: 20220718USDDSA9407803873BLUEUSNY001
Amount: USD 125,000
From: BLUEUSNY001
To: GRENCHZZ002
```

---

### **Query Example 2: Find All Transactions from a Bank**

```sparql
PREFIX fin: <http://example.org/financial/ontology#>

SELECT ?signal ?timestamp ?amount
WHERE {
    ?signal fin:fromInstitution ?bank .
    ?bank fin:bic "BLUEUSNY001" .
    ?signal fin:timestamp ?timestamp .
    ?signal fin:hasAmount ?amountObj .
    ?amountObj fin:value ?amount .
}
ORDER BY ?timestamp
```

---

### **Query Example 3: Customer-Requested Cancellations**

```sparql
PREFIX fin: <http://example.org/financial/ontology#>

SELECT ?signal ?amount ?currency
WHERE {
    ?signal a fin:PaymentCancellation .
    ?signal fin:hasReason ?reason .
    ?reason fin:reasonCode "CUST" .
    ?signal fin:hasAmount ?amountObj .
    ?amountObj fin:value ?amount .
    ?amountObj fin:currency ?currency .
}
```

---

## **Visual: The Ontology Graph**

```
                    ┌─────────────────────┐
                    │ PaymentCancellation │
                    │  (Your Signal)      │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
      ┌──────────┐      ┌──────────┐    ┌──────────┐
      │  Amount  │      │   From   │    │    To    │
      │          │      │Institution│   │Institution│
      └──────────┘      └──────────┘    └──────────┘
      │                 │                │
      ├─ value: 125000  ├─ bic: BLUE... ├─ bic: GREN...
      └─ currency: USD  └─ id: bluebank └─ id: greenbank
              │
              ▼
      ┌──────────────┐
      │ Transaction  │
      │  (Original)  │
      └──────────────┘
      │
      ├─ txId: 455d2a5f...
      ├─ e2eId: 8f01d8db...
      └─ msgId: 202207...
              │
              ▼
      ┌──────────────┐
      │    Reason    │
      └──────────────┘
      │
      └─ code: CUST
```

**Each node is a "thing" (entity)**
**Each arrow is a "relationship" (property)**
**Everything has semantic meaning**

---

## **What the Ontology Provides**

### **1. Type Definitions**
```turtle
fin:PaymentCancellation
    a owl:Class ;
    rdfs:subClassOf fin:FinancialSignal ;
    rdfs:label "Payment Cancellation"@en .
```
→ "A payment cancellation IS A type of financial signal"

### **2. Relationship Definitions**
```turtle
fin:hasAmount
    a owl:ObjectProperty ;
    rdfs:domain fin:FinancialSignal ;
    rdfs:range fin:Amount .
```
→ "Financial signals HAVE amounts"

### **3. Property Definitions**
```turtle
fin:value
    a owl:DatatypeProperty ;
    rdfs:domain fin:Amount ;
    rdfs:range xsd:decimal .
```
→ "Amounts have numeric values"

---

## **Formats Available**

Your RDF can be exported in multiple formats:

| Format | File | Use Case |
|--------|------|----------|
| **Turtle** | .ttl | Human-readable, debugging |
| **JSON-LD** | .jsonld | JavaScript apps, web |
| **RDF/XML** | .rdf | Java tools, Apache Jena |
| **N-Triples** | .nt | Simple line-by-line format |
| **N3** | .n3 | Extended features |

All contain the **same semantic information**, just different syntax!

---

## **Your Data Flow**

```
┌──────────────────┐
│  Your XML File   │
│  (6 KB)          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Signal Extractor │  ← financial_signal_extraction.py
│                  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Signal Object   │  ← PaymentCancellationSignal
│  (Python)        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Ontology Mapper  │  ← financial_ontology_mapper.py
│                  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  RDF Graph       │  ← 188 triples
│  (Semantic)      │
└────────┬─────────┘
         │
         ├─→ Save to file (.ttl, .jsonld, .rdf)
         ├─→ Query with SPARQL
         ├─→ Load to Neo4j
         └─→ Link to other graphs
```

---

## **Why This Matters**

### **Without Ontology (Just JSON):**
- "This is data about payments"
- Hard to query across different sources
- No semantic relationships
- Can't reason or infer

### **With Ontology (RDF):**
- "This IS a payment cancellation that HAS an amount and is FROM an institution"
- Can query: "Show me all high-value cancellations from troubled banks"
- Can reason: "5 cancellations in 1 hour = fraud pattern"
- Can link: Connect to regulatory data, fraud databases, etc.

---

## **Next Steps**

### **What You Can Do Now:**

1. **Run the demo:**
   ```bash
   python demo_ontology_mapping.py
   ```

2. **Test with your data:**
   ```bash
   python demo_ontology_mapping.py your_file.xml
   ```

3. **Query your RDF:**
   ```python
   from src.ontology import FinancialSignalToRDFMapper
   
   mapper = FinancialSignalToRDFMapper()
   # ... load signals ...
   
   results = mapper.query("""
       SELECT ?amount WHERE {
           ?signal fin:hasAmount ?amountObj .
           ?amountObj fin:value ?amount .
       }
   """)
   ```

4. **Use the API:**
   ```bash
   curl -X POST http://localhost:8000/ontology/map \
     -d '{"data": "<XML>"}' > output.ttl
   ```

---

## **Key Files**

| File | Purpose |
|------|---------|
| `financial_ontology.ttl` | Schema definition (what things ARE) |
| `financial_ontology_mapper.py` | Converter (signals → RDF) |
| `demo_ontology_mapping.py` | Complete demo |
| `your_payment_cancellation.ttl` | YOUR data as RDF |

---

**You now have semantic, queryable, linked data! 🎉**
