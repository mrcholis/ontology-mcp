#!/usr/bin/env python3
"""
XML to RDF via API

Drop an XML file, get RDF file back.

Usage:
    python xml_to_rdf.py your_file.xml
    python xml_to_rdf.py your_file.xml --format jsonld
    python xml_to_rdf.py your_file.xml --output custom_name.ttl
"""

import requests
import sys
import argparse
from pathlib import Path


def xml_to_rdf_via_api(
    xml_file: str,
    output_file: str = None,
    rdf_format: str = "turtle",
    api_url: str = "http://localhost:8000/ontology/map"
):
    """
    Send XML to API and get RDF back.
    
    Args:
        xml_file: Path to ISO 20022 XML file
        output_file: Where to save RDF (optional, auto-generated if not provided)
        rdf_format: RDF format (turtle, json-ld, xml, nt)
        api_url: API endpoint URL
    """
    
    # Read XML file
    print(f"📥 Reading XML file: {xml_file}")
    try:
        with open(xml_file, 'r') as f:
            xml_content = f.read()
    except FileNotFoundError:
        print(f"❌ Error: File not found: {xml_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        sys.exit(1)
    
    # Prepare request
    payload = {
        "data": xml_content,
        "data_format": rdf_format
    }
    
    # Send to API
    print(f"🌐 Sending to API: {api_url}")
    print(f"📊 Requested format: {rdf_format}")
    
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to API. Is it running?")
        print("   Start it with: python -m src.api.financial_ontology_api")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("❌ Error: Request timed out")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"   Response: {response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    # Check response
    if response.status_code != 200:
        print(f"❌ API returned error: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    # Get RDF content
    rdf_content = response.text
    
    # Check if we got triples
    triples_header = response.headers.get('X-RDF-Triples', '0')
    signal_count = response.headers.get('X-Signal-Count', '0')
    
    print(f"✅ Received RDF!")
    print(f"   Signals extracted: {signal_count}")
    print(f"   RDF triples: {triples_header}")
    
    # Determine output filename
    if output_file is None:
        input_path = Path(xml_file)
        extensions = {
            "turtle": ".ttl",
            "json-ld": ".jsonld",
            "xml": ".rdf",
            "nt": ".nt"
        }
        ext = extensions.get(rdf_format, ".ttl")
        output_file = f"output/{input_path.stem}_rdf{ext}"
    
    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save RDF file
    print(f"💾 Saving RDF to: {output_file}")
    with open(output_file, 'w') as f:
        f.write(rdf_content)
    
    file_size = output_path.stat().st_size
    print(f"✅ Done! File size: {file_size:,} bytes")
    print(f"\n📄 View your RDF file:")
    print(f"   cat {output_file}")
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Convert ISO 20022 XML to RDF via API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (creates output/filename_rdf.ttl)
  python xml_to_rdf.py your_payment.xml
  
  # Specify output format
  python xml_to_rdf.py your_payment.xml --format json-ld
  
  # Custom output filename
  python xml_to_rdf.py your_payment.xml --output my_custom.ttl
  
  # Different API endpoint
  python xml_to_rdf.py your_payment.xml --api http://localhost:8001/ontology/map

Available formats:
  turtle   - Turtle format (.ttl) - human-readable
  json-ld  - JSON-LD (.jsonld) - for web apps
  xml      - RDF/XML (.rdf) - for Java tools
  nt       - N-Triples (.nt) - simple line format
        """
    )
    
    parser.add_argument(
        'xml_file',
        help='ISO 20022 XML file to convert'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output RDF file (default: auto-generated in output/ folder)'
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=['turtle', 'json-ld', 'xml', 'nt'],
        default='turtle',
        help='RDF output format (default: turtle)'
    )
    
    parser.add_argument(
        '--api',
        default='http://localhost:8000/ontology/map',
        help='API endpoint URL (default: http://localhost:8000/ontology/map)'
    )
    
    args = parser.parse_args()
    
    # Convert
    print("\n" + "=" * 70)
    print("  XML → RDF Converter (via API)")
    print("=" * 70 + "\n")
    
    output_file = xml_to_rdf_via_api(
        xml_file=args.xml_file,
        output_file=args.output,
        rdf_format=args.format,
        api_url=args.api
    )
    
    print("\n" + "=" * 70)
    print("  ✅ Conversion Complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python xml_to_rdf.py your_file.xml")
        print("Try: python xml_to_rdf.py --help")
        sys.exit(1)
    
    main()