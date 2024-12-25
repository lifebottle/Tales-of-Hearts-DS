from pathlib import Path
import os
import pytest
import pyjson5 as json
from pythonlib.formats.structnode import StructNode, StructEntry
from pythonlib.formats.FileIO import FileIO

#NPC Struct with 6 Unknowns
#More than 2 entries + End Unknown = 0x0
def test_struct_npc1(npc_struct1):
    assert npc_struct1.nb_unknowns == 6
    assert npc_struct1.speaker.jap_text != ""
    assert len(npc_struct1.end_unknowns) == 1
    assert len(npc_struct1.texts_entry) == 8

#Story Struct
def test_struct_story1(story_struct1):
    assert story_struct1.nb_unknowns == 2
    assert story_struct1.speaker.jap_text != ""
    assert len(story_struct1.end_unknowns) == 0
    assert len(story_struct1.texts_entry) == 1

#Story Struct2
def test_struct_story2(story_struct2):
    assert story_struct2.nb_unknowns == 2
    assert story_struct2.speaker.jap_text != ""
    assert len(story_struct2.end_unknowns) == 0
    assert len(story_struct2.texts_entry) == 1

#String Struct Normal
def test_struct_string1(string_struct1):
    assert string_struct1.nb_unknowns == 0
    assert string_struct1.speaker.jap_text == "Variable"
    assert len(string_struct1.end_unknowns) == 0
    assert len(string_struct1.texts_entry) == 1

def test_string_end_of_file(string_end_of_file1, string_end_of_file2):
    assert string_end_of_file1.nb_unknowns == 0
    assert string_end_of_file1.speaker.jap_text == "Variable"
    assert len(string_end_of_file1.end_unknowns) == 0
    assert len(string_end_of_file1.texts_entry) == 1

    assert string_end_of_file2.nb_unknowns == 0
    assert string_end_of_file2.speaker.jap_text == "Variable"
    assert len(string_end_of_file2.end_unknowns) == 0
    assert len(string_end_of_file2.texts_entry) == 1

def test_string_struct_weird(string_struct_weird):
    assert string_struct_weird.nb_unknowns == 0
    assert string_struct_weird.speaker.jap_text == "Variable"
    assert len(string_struct_weird.texts_entry) == 10

@pytest.fixture
def npc_struct1():
    text_offset = 0x1ECA8
    path = Path('./pythonlib/tests/TOH/files/FSHT00.SCP')
    file_size = os.path.getsize(path)
    section = 'NPC'

    with FileIO(path) as tss:
        tss.seek(0xC)
        strings_offset = tss.read_uint32()

        node = StructNode(id=0, pointer_offset=0,
                       text_offset=text_offset,
                       tss=tss, strings_offset=strings_offset, file_size=file_size,
                       section=section)

        return node


@pytest.fixture
def story_struct1():
    text_offset = 0x1FBF8
    path = Path('./pythonlib/tests/TOH/files/FSHT00.SCP')
    file_size = os.path.getsize(path)
    section = 'Story'

    with FileIO(path) as tss:
        tss.seek(0xC)
        strings_offset = tss.read_uint32()

        node = StructNode(id=0, pointer_offset=0,
                       text_offset=text_offset,
                       tss=tss, strings_offset=strings_offset, file_size=file_size,
                       section=section)

        return node

@pytest.fixture
def story_struct2():
    text_offset = 0x14158
    path = Path('./pythonlib/tests/TOH/files/VOLD01P.SCP')
    file_size = os.path.getsize(path)
    section = 'Story'

    with FileIO(path) as tss:
        tss.seek(0xC)
        strings_offset = tss.read_uint32()

        node = StructNode(id=0, pointer_offset=0,
                       text_offset=text_offset,
                       tss=tss, strings_offset=strings_offset, file_size=file_size,
                       section=section)

        return node

@pytest.fixture
def string_struct1():
    text_offset = 0x1C540
    path = Path('./pythonlib/tests/TOH/files/AMUT01P.SCP')
    file_size = os.path.getsize(path)
    section = 'Misc'

    with FileIO(path) as tss:
        tss.seek(0xC)
        strings_offset = tss.read_uint32()

        node = StructNode(id=0, pointer_offset=0,
                       text_offset=text_offset,
                       tss=tss, strings_offset=strings_offset, file_size=file_size,
                       section=section)

        return node

@pytest.fixture
def string_struct2():
    path = Path('./pythonlib/tests/TOH/files/STRT00.SCP')
    file_size = os.path.getsize(path)
    text_offset = 0x14DE8
    section = 'Story'

    with FileIO(path) as tss:
        tss.seek(0xC)
        strings_offset = tss.read_uint32()

        node = StructNode(id=0, pointer_offset=0,
                       text_offset=text_offset,
                       tss=tss, strings_offset=strings_offset, file_size=file_size,
                       section=section)

        return node

@pytest.fixture
def string_end_of_file1():
    text_offset = 0x1C5F5
    path = Path('./pythonlib/tests/TOH/files/AMUT01P.SCP')
    file_size = os.path.getsize(path)
    section = 'Misc'

    with FileIO(path) as tss:
        tss.seek(0xC)
        strings_offset = tss.read_uint32()

        node = StructNode(id=0, pointer_offset=0,
                       text_offset=text_offset,
                       tss=tss, strings_offset=strings_offset, file_size=file_size,
                       section=section)

        return node

@pytest.fixture
def string_end_of_file2():
    text_offset = 0x9D14
    path = Path('./pythonlib/tests/TOH/files/LITD04P.SCP')
    file_size = os.path.getsize(path)
    section = 'Misc'

    with FileIO(path) as tss:
        tss.seek(0xC)
        strings_offset = tss.read_uint32()

        node = StructNode(id=0, pointer_offset=0,
                       text_offset=text_offset,
                       tss=tss, strings_offset=strings_offset, file_size=file_size,
                       section=section)

        return node

@pytest.fixture
def string_struct_weird():
    text_offset = 0x9CEC
    path = Path('./pythonlib/tests/TOH/files/LITD04P.SCP')
    file_size = os.path.getsize(path)
    section = 'Misc'

    with FileIO(path) as tss:
        tss.seek(0xC)
        strings_offset = tss.read_uint32()

        node = StructNode(id=0, pointer_offset=0,
                       text_offset=text_offset,
                       tss=tss, strings_offset=strings_offset, file_size=file_size,
                       section=section)

        return node