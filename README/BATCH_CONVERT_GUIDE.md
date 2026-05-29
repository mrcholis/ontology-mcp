# 📦 Batch XML to RDF Converter Guide

## **What It Does**

Converts **multiple ISO 20022 XML files** to RDF format in one command.

Instead of:
```bash
python xml_to_rdf.py file1.xml
python xml_to_rdf.py file2.xml
python xml_to_rdf.py file3.xml
python xml_to_rdf.py file4.xml
```

Just do:
```bash
python batch_convert.py xml_files/
```

---

## **Quick Start**

### **Step 1: Make Sure API is Running**

```bash
# Terminal 1 - Start the API
python -m src.api.financial_ontology_api

# You should see:
# ✅ Financial Signal Extraction & Ontology API
# 🌐 http://localhost:8000
```

### **Step 2: Run Batch Converter**

```bash
# Terminal 2 - Convert all XML files
python batch_convert.py xml_files/
```

### **Step 3: Check Results**

```bash
# See generated RDF files
ls output/
```

---

## **Basic Usage**

### **Convert All Files in a Folder**

```bash
python batch_convert.py xml_files/
```

**What happens:**
- Finds all `.xml` files in `xml_files/`
- Converts each to RDF (Turtle format)
- Saves to `output/` folder
- Shows progress for each file

**Output:**
```
📂 Input: xml_files/
📂 Output: output/
📊 Format: turtle
📁 Found 4 XML file(s)

📥 Processing: camt026_unable_to_apply.xml
   ✅ Signals: 1 | Triples: 150 | Size: 35,241 bytes
   💾 Saved: camt026_unable_to_apply_rdf.ttl

📥 Processing: camt029_cancellation_rejected.xml
   ✅ Signals: 1 | Triples: 162 | Size: 38,456 bytes
   💾 Saved: camt029_cancellation_rejected_rdf.ttl

... (continues for all files)

======================================================================
  Conversion Complete
======================================================================

✅ Successful: 4
📂 All RDF files saved to: output/
```

---

## **Advanced Options**

### **1. Change Output Format**

Convert to JSON-LD instead of Turtle:

```bash
python batch_convert.py xml_files/ --format json-ld
```

**Available formats:**
- `turtle` - Turtle format (.ttl) - **Default, human-readable**
- `json-ld` - JSON-LD (.jsonld) - For web apps
- `xml` - RDF/XML (.rdf) - For Java tools
- `nt` - N-Triples (.nt) - Simple line format

---

### **2. Change Output Directory**

Save RDF files to a different folder:

```bash
python batch_convert.py xml_files/ --output rdf_output/
```

Files will be saved to `rdf_output/` instead of `output/`

---

### **3. Convert Specific Files (Glob Pattern)**

Convert only certain files:

```bash
# Only camt.05x files
python batch_convert.py "xml_files/camt05*.xml"

# Only cancellation-related files
python batch_convert.py "xml_files/*cancel*.xml"

# All files starting with 'test'
python batch_convert.py "xml_files/test*.xml"
```

⚠️ **Note:** Use quotes around patterns with `*`

---

### **4. Different API Endpoint**

If your API is on a different port:

```bash
python batch_convert.py xml_files/ --api http://localhost:8001/ontology/map
```

---

### **5. Combine All Options**

```bash
python batch_convert.py xml_files/ \
    --output my_rdf_files/ \
    --format json-ld \
    --api http://localhost:8000/ontology/map
```

---

## **Common Use Cases**

### **Use Case 1: Daily Batch Processing**

Process all new files each day:

```bash
#!/bin/bash
# daily_convert.sh

# Start API
python -m src.api.financial_ontology_api &
API_PID=$!

# Wait for API to start
sleep 3

# Convert all files
python batch_convert.py xml_files/

# Stop API
kill $API_PID
```

---

### **Use Case 2: Convert to Multiple Formats**

Generate all formats at once:

```bash
# Turtle (human-readable)
python batch_convert.py xml_files/ --format turtle --output output/turtle/

# JSON-LD (for web apps)
python batch_convert.py xml_files/ --format json-ld --output output/jsonld/

# RDF/XML (for Java tools)
python batch_convert.py xml_files/ --format xml --output output/rdfxml/
```

---

### **Use Case 3: Selective Processing**

Convert only specific message types:

```bash
# Only cancellations
python batch_convert.py "xml_files/camt056*.xml"

# Only statements
python batch_convert.py "xml_files/camt053*.xml"

# Only July 2022 files (if named with dates)
python batch_convert.py "xml_files/*202207*.xml"
```

---

## **What You Get**

### **Input Structure:**
```
xml_files/
├── camt026_unable_to_apply.xml
├── camt029_cancellation_rejected.xml
├── camt053_account_statement.xml
└── camt056_cancellation_request.xml
```

### **Output Structure:**
```
output/
├── camt026_unable_to_apply_rdf.ttl
├── camt029_cancellation_rejected_rdf.ttl
├── camt053_account_statement_rdf.ttl
└── camt056_cancellation_request_rdf.ttl
```

---

## **Progress Display**

For each file, you'll see:

```
📥 Processing: camt056_cancellation_request.xml
   ✅ Signals: 1          ← Number of signals extracted
   Triples: 188           ← Number of RDF triples created
   Size: 45,239 bytes     ← Output file size
   💾 Saved: camt056_cancellation_request_rdf.ttl
```

---

## **Error Handling**

### **API Not Running**

```
❌ Cannot connect to API. Is it running?
   Start with: python -m src.api.financial_ontology_api
```

**Fix:** Start the API first

---

### **No XML Files Found**

```
❌ No XML files found in: xml_files/
```

**Fix:** Check your folder path or add XML files

---

### **File Read Error**

```
❌ Error reading file: [Errno 2] No such file or directory
```

**Fix:** Check file permissions or path

---

## **Command Line Options**

### **Full Help:**

```bash
python batch_convert.py --help
```

### **Arguments:**

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `input_path` | - | Folder or pattern | *Required* |
| `--output` | `-o` | Output directory | `output/` |
| `--format` | `-f` | RDF format | `turtle` |
| `--api` | - | API endpoint URL | `http://localhost:8000/ontology/map` |

---

## **Tips & Best Practices**

### **✅ DO:**

- Start API before running batch converter
- Use descriptive file names (e.g., `camt056_cancellation_request.xml`)
- Check output folder after conversion
- Use `--format` for different needs (turtle for debugging, json-ld for web)

### **❌ DON'T:**

- Forget to start the API first
- Use patterns without quotes (use `"xml_files/*.xml"` not `xml_files/*.xml`)
- Mix message types in one query without organizing them

---

## **Integration with Other Tools**

### **After Batch Conversion:**

```bash
# 1. Convert all files
python batch_convert.py xml_files/

# 2. Query the RDF data
python sparql_query_examples.py output/camt056_cancellation_request_rdf.ttl

# 3. Build lifecycle view
python lifecycle_tracker.py output/
```

---

## **Troubleshooting**

### **Problem: "unrecognized arguments" error**

**Wrong:**
```bash
python batch_convert.py file1.xml file2.xml file3.xml
```

**Correct:**
```bash
python batch_convert.py xml_files/
```

---

### **Problem: Nothing happens**

**Check:**
1. Is API running? `curl http://localhost:8000/health`
2. Are there XML files? `ls xml_files/*.xml`
3. Do you have write permissions? `ls -la output/`

---

### **Problem: Some files fail**

The script continues even if some files fail. Check the summary:

```
✅ Successful: 3
❌ Failed: 1
```

Failed files will show error messages during processing.

---

## **Examples**

### **Example 1: Simple Batch**

```bash
python batch_convert.py xml_files/
```

Converts all XML files to Turtle format in `output/`

---

### **Example 2: Custom Output**

```bash
python batch_convert.py xml_files/ --output production_rdf/
```

Saves to `production_rdf/` folder

---

### **Example 3: Web-Friendly Format**

```bash
python batch_convert.py xml_files/ --format json-ld
```

Generates `.jsonld` files for web applications

---

### **Example 4: Selective Conversion**

```bash
python batch_convert.py "xml_files/camt05*.xml"
```

Only converts camt.053 and camt.056 files

---

## **Performance**

**Typical conversion times:**
- Small file (< 10 KB): ~0.5 seconds
- Medium file (10-50 KB): ~1-2 seconds
- Large file (> 50 KB): ~2-5 seconds

**For 100 files:** ~3-5 minutes total

---

## **File Naming Convention**

The script automatically names output files:

**Input:** `camt056_cancellation_request.xml`  
**Output:** `camt056_cancellation_request_rdf.ttl`

**Pattern:** `{original_name}_rdf.{extension}`

Extensions:
- `.ttl` for turtle
- `.jsonld` for json-ld
- `.rdf` for xml
- `.nt` for nt

---

## **Next Steps**

After batch conversion:

1. **Query the data:** Use SPARQL to analyze relationships
2. **Build lifecycle views:** Track message flows
3. **Visualize:** Create graphs showing connections
4. **Load to database:** Import into Neo4j or GraphDB

---

## **Summary**

**One command converts all your XML files:**

```bash
python batch_convert.py xml_files/
```

**That's it!** ✨

All your ISO 20022 messages are now semantic RDF data ready for querying, analysis, and integration.

---

## **Quick Reference Card**

```bash
# Basic
python batch_convert.py xml_files/

# Different format
python batch_convert.py xml_files/ --format json-ld

# Custom output
python batch_convert.py xml_files/ --output my_folder/

# Specific files
python batch_convert.py "xml_files/camt05*.xml"

# All options
python batch_convert.py xml_files/ -o output/ -f turtle --api http://localhost:8000/ontology/map
```

---

**Happy converting!** 🚀