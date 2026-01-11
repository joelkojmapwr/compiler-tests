import subprocess
import os

class CompilerTestRunner:
    def __init__(self):
        pass


    def compile(self, input_file, output_file):
        result = subprocess.run(['python3', 'main.py', input_file, output_file], 
                               capture_output=True, text=True)
        # print(f"=== Output for {input_file} ===")
        # if result.stdout:
        #     print("STDOUT:")
        #     print(result.stdout)
        # if result.stderr:
        #     print("STDERR:")
        #     print(result.stderr)
        # if result.returncode != 0:
        #     print(f"Process failed with return code: {result.returncode}")
        return result

class VMRunner:
    def __init__(self):
        pass

    def run_on_vm(self, input_file, stdin_file):
        try:
            with open(stdin_file, 'r') as f:
                stdin_content = f.read()
                result = subprocess.run(['../mw2025/maszyna-wirtualna', input_file], 
                        capture_output=True, text=True, input=stdin_content)
        except (FileNotFoundError, OSError):
            result = subprocess.run(['../mw2025/maszyna-wirtualna', input_file], 
                       capture_output=True, text=True)
        print(f"=== Output for {input_file} ===")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        if result.returncode != 0:
            print(f"Process failed with return code: {result.returncode}")
        return result
    
class VMOutputValidator:
    def __init__(self):
        pass
    
    def _parse_vm_output(self, vm_output: str) -> str:
        lines = vm_output.strip().split('\n')
        result_lines = []
        for line in lines:
            if '>' in line:
                result_lines.append(line.split('>', 1)[1].lstrip(' '))
        return '\n'.join(result_lines)

    def validate(self, vm_output: str, expected_result_file):
        parsed_output = self._parse_vm_output(vm_output)
        with open(expected_result_file, 'r') as f:
            expected_output = f.read().strip()
            
        parsed_lines = parsed_output.split('\n')
        expected_lines = expected_output.split('\n')

        assert len(parsed_lines) == len(expected_lines), f"Different number of lines: got {len(parsed_lines)}, expected {len(expected_lines)}"

        for i, (parsed_line, expected_line) in enumerate(zip(parsed_lines, expected_lines)):
            assert parsed_line == expected_line, f"Line {i+1} differs: got '{parsed_line}', expected '{expected_line}'"


def test_programs():
    programs_dir = "tests/programs"
    test_runner = CompilerTestRunner()
    vm_runner = VMRunner()
    vm_output_validator = VMOutputValidator()
    test_dirs = ["read_write"]
    for test_dir in test_dirs:
        
        for filename in os.listdir(f"{programs_dir}/{test_dir}"):
            if filename.endswith(".imp"):
                input_file = os.path.join(programs_dir, test_dir, filename)
                output_file = input_file.replace("imp", "mr")
                stdin_file = input_file.replace("imp", "in")
                expected_result_file = input_file.replace("imp", "res")
                try:
                    test_runner.compile(input_file, output_file)
                except Exception as e:
                    print(f"Error compiling {filename}: {e}")
                    continue

                result = vm_runner.run_on_vm(output_file, stdin_file)
                vm_output_validator.validate(result.stdout, expected_result_file)
            