import os
from pathlib import Path
from pythonlib.games import ToolsTOH
from pythonlib.formats.FileIO import FileIO
from pythonlib.formats.text_toh import bytes_to_text, text_to_bytes
import pytest
import pyjson5 as json
import pdb
from io import BytesIO
base_path = Path('pythonlib/tests/TOH')


@pytest.mark.parametrize("n", [0,1,2])
def test_colors_to_text(config_bytes, n):
    input = config_bytes[n]['byte']
    input_bytes = bytes.fromhex(input.replace(' ',''))
    with FileIO(base_path / 'colors_to_text.bin', 'wb+') as f:
        f.write(input_bytes)
        f.write(b'\x00')
        f.seek(0)
        expected = config_bytes[n]['text']
        res, buffer = bytes_to_text(f,0)
        assert res == expected
        assert buffer == input_bytes


@pytest.mark.parametrize("n", [3,4,5])
def test_names_to_text(config_bytes, n):
    input = config_bytes[n]['byte']
    input_bytes = bytes.fromhex(input.replace(' ', ''))
    with FileIO(base_path / 'names_to_text.bin', 'wb+') as f:
        f.write(input_bytes)
        f.write(b'\x00')
        f.seek(0)
        expected = config_bytes[n]['text']
        res, buffer = bytes_to_text(f, 0)
        assert res == expected
        assert buffer == input_bytes


@pytest.mark.parametrize("n", [6,7,8])
def test_buttons_to_text(config_bytes, n):
    input = config_bytes[n]['byte']
    input_bytes = bytes.fromhex(input.replace(' ', ''))
    with FileIO(base_path / 'buttons_to_text.bin', 'wb+') as f:
        f.write(input_bytes)
        f.write(b'\x00')
        f.seek(0)
        expected = config_bytes[n]['text']
        res, buffer = bytes_to_text(f, 0)
        assert res == expected
        assert buffer == input_bytes


@pytest.mark.parametrize("n", [9,10,11,12,13,14])
def test_voiceid_to_text(config_bytes, n):
    input = config_bytes[n]['byte']
    input_bytes = bytes.fromhex(input.replace(' ', ''))
    with FileIO(base_path / 'voice_to_text.bin', 'wb+') as f:
        f.write(input_bytes)
        f.write(b'\x00')
        f.seek(0)
        expected = config_bytes[n]['text']
        res, buffer = bytes_to_text(f, 0)
        assert res == expected
        assert buffer == input_bytes


@pytest.mark.parametrize("n", [0,1,2])
def test_colors_to_bytes(config_text, n):
    input = config_text[n]['text']
    expected = bytes.fromhex(config_text[n]['byte'].replace(' ',''))
    res = text_to_bytes(input)
    assert res.hex() == expected.hex()


@pytest.mark.parametrize("n", [3,4,5])
def test_names_to_bytes(config_text, n):
    input = config_text[n]['text']
    expected = bytes.fromhex(config_text[n]['byte'].replace(' ',''))
    res = text_to_bytes(input)
    assert res.hex() == expected.hex()

@pytest.mark.parametrize("n", [6,7,8])
def test_buttons_to_bytes(config_text, n):
    input = config_text[n]['text']
    expected = bytes.fromhex(config_text[n]['byte'].replace(' ',''))
    res = text_to_bytes(input)
    assert res.hex() == expected.hex()

@pytest.mark.parametrize("n", [9,10,11,12,13,14])
def test_voiceid_to_bytes(config_text, n):
    input = config_text[n]['text']
    expected = bytes.fromhex(config_text[n]['byte'].replace(' ',''))
    res = text_to_bytes(input)
    assert res.hex() == expected.hex()

@pytest.mark.parametrize("n", [15,16,17,18,19])
def test_misc(config_text, n):
    input = config_text[n]['text']
    expected = bytes.fromhex(config_text[n]['byte'].replace(' ',''))
    res = text_to_bytes(input)
    assert res.hex() == expected.hex()



@pytest.fixture
def tales_instance():
    insert_mask = [
        '--with-editing', '--with-proofreading'
    ]
    tales_instance = ToolsTOH.ToolsTOH(
        project_file=Path(os.path.join(os.getcwd(), '..','TOH', 'project.json')),
        insert_mask=insert_mask,
        changed_only=False)
    return tales_instance

@pytest.fixture
def config_bytes():
    with open(base_path / 'test_tags.json', encoding='utf-8') as f:
        json_data = json.load(f)
        return [{"byte":k, "text":json_data[k]} for k in json_data.keys()]

@pytest.fixture
def config_text():
    with open(base_path / 'test_tags.json', encoding='utf-8') as f:
        json_data = json.load(f)
        return [{"text":json_data[k], "byte":k} for k in json_data.keys()]
