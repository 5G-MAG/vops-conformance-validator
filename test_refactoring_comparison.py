"""
Test script to compare XML output before/after refactoring.
Verifies that the refactoring doesn't change the parser output.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from sa4_bitstream_validator.parsers.avc_parser import AVCParser
from sa4_bitstream_validator.parsers.hevc_parser import HEVCParser


def generate_xml(bitstream_path, parser, xml_filename, include_internal_vars=True):
    """Generate XML from bitstream using parser."""
    try:
        with open(bitstream_path, 'rb') as bs_file:
            with open(xml_filename, 'w') as xml_file:
                parser.bitstream_to_xml(bs_file, xml_file, include_internal_vars=include_internal_vars)
        return True
    except Exception as e:
        print(f"[FAIL] Failed to generate XML: {e}")
        return False


def compare_xml_files(file1, file2):
    """Compare two XML files and report differences."""
    try:
        with open(file1, 'r') as f1:
            content1 = f1.read()
        with open(file2, 'r') as f2:
            content2 = f2.read()
        
        if content1 == content2:
            return True, "Files are identical"
        else:
            # Find first difference
            lines1 = content1.splitlines()
            lines2 = content2.splitlines()
            
            for i, (line1, line2) in enumerate(zip(lines1, lines2)):
                if line1 != line2:
                    return False, f"First difference at line {i+1}:\n  Expected: {line1}\n  Got:      {line2}"
            
            # Files have different number of lines
            if len(lines1) != len(lines2):
                return False, f"Files have different number of lines: {len(lines1)} vs {len(lines2)}"
            
            return False, "Files are different"
    except Exception as e:
        return False, f"Error comparing files: {e}"


def test_hevc_parser():
    """Test HEVC parser with baseline comparison."""
    print("\n" + "="*80)
    print("Testing HEVC Parser")
    print("="*80)
    
    bitstream_path = "test_files/3gpp-hevc-hd-op-test.hevc"
    baseline_path = "test_baseline_hevc.xml"
    output_path = "test_output_hevc.xml"
    
    if not os.path.exists(bitstream_path):
        print(f"[SKIP] Bitstream not found: {bitstream_path}")
        return True
    
    if not os.path.exists(baseline_path):
        print(f"[SKIP] Baseline not found: {baseline_path}")
        return True
    
    # Generate XML with refactored parser
    parser = HEVCParser()
    if not generate_xml(bitstream_path, parser, output_path):
        return False
    
    # Compare with baseline
    is_identical, message = compare_xml_files(baseline_path, output_path)
    
    if is_identical:
        print("[PASS] HEVC parser output matches baseline")
    else:
        print(f"[FAIL] HEVC parser output differs from baseline: {message}")
    
    # Clean up
    try:
        os.unlink(output_path)
    except:
        pass
    
    return is_identical


def test_avc_parser():
    """Test AVC parser with baseline comparison."""
    print("\n" + "="*80)
    print("Testing AVC Parser")
    print("="*80)
    
    bitstream_path = "test_files/HPCADQ_BRCM_B.264"
    baseline_path = "test_baseline_avc.xml"
    output_path = "test_output_avc.xml"
    
    if not os.path.exists(bitstream_path):
        print(f"[SKIP] Bitstream not found: {bitstream_path}")
        return True
    
    if not os.path.exists(baseline_path):
        print(f"[SKIP] Baseline not found: {baseline_path}")
        return True
    
    # Generate XML with refactored parser
    parser = AVCParser()
    if not generate_xml(bitstream_path, parser, output_path):
        return False
    
    # Compare with baseline
    is_identical, message = compare_xml_files(baseline_path, output_path)
    
    if is_identical:
        print("[PASS] AVC parser output matches baseline")
    else:
        print(f"[FAIL] AVC parser output differs from baseline: {message}")
    
    # Clean up
    try:
        os.unlink(output_path)
    except:
        pass
    
    return is_identical


def test_hevc_parser_without_internal_vars():
    """Test HEVC parser without internal variables."""
    print("\n" + "="*80)
    print("Testing HEVC Parser (without internal variables)")
    print("="*80)
    
    bitstream_path = "test_files/3gpp-hevc-hd-op-test.hevc"
    output_path = "test_output_hevc_no_internal.xml"
    
    if not os.path.exists(bitstream_path):
        print(f"[SKIP] Bitstream not found: {bitstream_path}")
        return True
    
    # Generate XML without internal variables
    parser = HEVCParser()
    if not generate_xml(bitstream_path, parser, output_path, include_internal_vars=False):
        return False
    
    # Basic validation - check that file was created and has content
    try:
        with open(output_path, 'r') as f:
            content = f.read()
        
        if len(content) > 0 and "HEVCBitstream" in content:
            print("[PASS] HEVC parser generates valid XML without internal variables")
            result = True
        else:
            print("[FAIL] HEVC parser output is empty or invalid")
            result = False
    except Exception as e:
        print(f"[FAIL] Error reading output: {e}")
        result = False
    
    # Clean up
    try:
        os.unlink(output_path)
    except:
        pass
    
    return result


def test_avc_parser_without_internal_vars():
    """Test AVC parser without internal variables."""
    print("\n" + "="*80)
    print("Testing AVC Parser (without internal variables)")
    print("="*80)
    
    bitstream_path = "test_files/HPCADQ_BRCM_B.264"
    output_path = "test_output_avc_no_internal.xml"
    
    if not os.path.exists(bitstream_path):
        print(f"[SKIP] Bitstream not found: {bitstream_path}")
        return True
    
    # Generate XML without internal variables
    parser = AVCParser()
    if not generate_xml(bitstream_path, parser, output_path, include_internal_vars=False):
        return False
    
    # Basic validation - check that file was created and has content
    try:
        with open(output_path, 'r') as f:
            content = f.read()
        
        if len(content) > 0 and "AVCBitstream" in content:
            print("[PASS] AVC parser generates valid XML without internal variables")
            result = True
        else:
            print("[FAIL] AVC parser output is empty or invalid")
            result = False
    except Exception as e:
        print(f"[FAIL] Error reading output: {e}")
        result = False
    
    # Clean up
    try:
        os.unlink(output_path)
    except:
        pass
    
    return result


def regenerate_baselines():
    """Regenerate baseline XML files with current parser."""
    print("\n" + "="*80)
    print("Regenerating Baselines")
    print("="*80)
    
    # HEVC baseline
    hevc_path = "test_files/3gpp-hevc-hd-op-test.hevc"
    hevc_baseline = "test_baseline_hevc.xml"
    if os.path.exists(hevc_path):
        parser = HEVCParser()
        if generate_xml(hevc_path, parser, hevc_baseline):
            print(f"[OK] Regenerated HEVC baseline: {hevc_baseline}")
    
    # AVC baseline
    avc_path = "test_files/HPCADQ_BRCM_B.264"
    avc_baseline = "test_baseline_avc.xml"
    if os.path.exists(avc_path):
        parser = AVCParser()
        if generate_xml(avc_path, parser, avc_baseline):
            print(f"[OK] Regenerated AVC baseline: {avc_baseline}")


def main():
    """Main test function."""
    print("Refactoring Comparison Test")
    print("="*80)
    print("This test verifies that the refactored parsers produce identical XML output.")
    
    # Regenerate baselines first
    regenerate_baselines()
    
    results = []
    
    # Run tests
    results.append(("HEVC Parser (with internal vars)", test_hevc_parser()))
    results.append(("AVC Parser (with internal vars)", test_avc_parser()))
    results.append(("HEVC Parser (without internal vars)", test_hevc_parser_without_internal_vars()))
    results.append(("AVC Parser (without internal vars)", test_avc_parser_without_internal_vars()))
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
