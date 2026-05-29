#!/usr/bin/env python3
"""
Batch XML to RDF Converter

Converts all XML files in a folder to RDF format via API.

Usage:
    python batch_convert.py xml_files/
    python batch_convert.py xml_files/ --format json-ld
    python batch_convert.py xml_files/*.xml
"""

import requests
import sys
import argparse
from pathlib import Path
from typing import List


def convert_file(
    xml_file: Path,
    output_dir: Path,
    rdf_format: str = "turtle",
    api_url: str = "http://localhost:8000/ontology/map"
) -> bool:
    """
    Convert a single XML file to RDF.
    
    Args:
        xml_file: Path to XML file
        output_dir: Where to save RDF files
        rdf_format: RDF format (turtle, json-ld, xml, nt)
        api_url: API endpoint URL
        
    Returns:
        True if successful, False otherwise
    """
    
    print(f"📥 Processing: {xml_file.name}")
    
    # Read XML
    try:
        with open(xml_file, 'r') as f:
            xml_content = f.read()
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
        return False
    
    # Prepare request
    payload = {
        "data": xml_content,
        "data_format": rdf_format
    }
    
    # Send to API
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to API. Is it running?")
        print(f"      Start with: python -m src.api.financial_ontology_api")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timed out")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP Error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Get RDF content
    rdf_content = response.text
    
    # Get stats from headers
    triples = response.headers.get('X-RDF-Triples', '?')
    signals = response.headers.get('X-Signal-Count', '?')
    
    # Determine output filename
    extensions = {
        "turtle": ".ttl",
        "json-ld": ".jsonld",
        "xml": ".rdf",
        "nt": ".nt"
    }
    ext = extensions.get(rdf_format, ".ttl")
    output_file = output_dir / f"{xml_file.stem}_rdf{ext}"
    
    # Save RDF file
    try:
        with open(output_file, 'w') as f:
            f.write(rdf_content)
    except Exception as e:
        print(f"   ❌ Error saving file: {e}")
        return False
    
    file_size = output_file.stat().st_size
    
    print(f"   ✅ Signals: {signals} | Triples: {triples} | Size: {file_size:,} bytes")
    print(f"   💾 Saved: {output_file.name}")
    
    return True


def batch_convert(
    input_path: str,
    output_dir: str = "output",
    rdf_format: str = "turtle",
    api_url: str = "http://localhost:8000/ontology/map"
):
    """
    Batch convert XML files to RDF.
    
    Args:
        input_path: Path to folder or file pattern (e.g., xml_files/ or xml_files/*.xml)
        output_dir: Where to save RDF files
        rdf_format: RDF output format
        api_url: API endpoint URL
    """
    
    # Parse input path
    input_path_obj = Path(input_path)
    
    # Find XML files
    xml_files: List[Path] = []
    
    if input_path_obj.is_dir():
        # It's a directory - find all XML files
        xml_files = list(input_path_obj.glob("*.xml"))
    elif input_path_obj.is_file():
        # It's a single file
        xml_files = [input_path_obj]
    elif "*" in input_path:
        # It's a glob pattern
        parent = Path(input_path).parent
        pattern = Path(input_path).name
        xml_files = list(parent.glob(pattern))
    else:
        print(f"❌ Invalid path: {input_path}")
        return
    
    if not xml_files:
        print(f"❌ No XML files found in: {input_path}")
        return
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Convert all files
    print("\n" + "=" * 70)
    print("  Batch XML → RDF Converter")
    print("=" * 70)
    print(f"\n📂 Input: {input_path}")
    print(f"📂 Output: {output_dir}")
    print(f"📊 Format: {rdf_format}")
    print(f"📁 Found {len(xml_files)} XML file(s)\n")
    
    successful = 0
    failed = 0
    
    for xml_file in xml_files:
        if convert_file(xml_file, output_path, rdf_format, api_url):
            successful += 1
        else:
            failed += 1
        print()  # Blank line between files
    
    # Summary
    print("=" * 70)
    print("  Conversion Complete")
    print("=" * 70)
    print(f"\n✅ Successful: {successful}")
    
    if failed > 0:
        print(f"❌ Failed: {failed}")
    
    print(f"\n📂 All RDF files saved to: {output_dir}/")
    
    # List output files
    output_files = list(output_path.glob(f"*{extensions.get(rdf_format, '.ttl')}"))
    if output_files:
        print(f"\n📄 Generated files:")
        for f in sorted(output_files):
            print(f"   • {f.name}")
    
    print()


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="Batch convert ISO 20022 XML files to RDF via API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all XML files in a folder
  python batch_convert.py xml_files/
  
  # Convert with specific format
  python batch_convert.py xml_files/ --format json-ld
  
  # Specify output directory
  python batch_convert.py xml_files/ --output rdf_output/
  
  # Use glob pattern
  python batch_convert.py "xml_files/camt*.xml"

Available formats:
  turtle   - Turtle format (.ttl) - human-readable
  json-ld  - JSON-LD (.jsonld) - for web apps
  xml      - RDF/XML (.rdf) - for Java tools
  nt       - N-Triples (.nt) - simple line format
        """
    )
    
    parser.add_argument(
        'input_path',
        help='Folder containing XML files or file pattern (e.g., xml_files/ or xml_files/*.xml)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='Output directory for RDF files (default: output/)'
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
    
    batch_convert(
        input_path=args.input_path,
        output_dir=args.output,
        rdf_format=args.format,
        api_url=args.api
    )


# Map format to extension
extensions = {
    "turtle": ".ttl",
    "json-ld": ".jsonld",
    "xml": ".rdf",
    "nt": ".nt"
}


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python batch_convert.py xml_files/")
        print("Try: python batch_convert.py --help")
        sys.exit(1)
    
    main()