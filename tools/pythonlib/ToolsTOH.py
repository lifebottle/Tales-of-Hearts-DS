import os
import shutil
from os import stat_result

import pandas as pd

from pathlib import Path
import pyjson5 as json
import subprocess
import datetime
import lxml.etree as etree
from tools.pythonlib.formats.FileIO import FileIO
from tools.pythonlib.formats.fps4 import Fps4
from tools.pythonlib.formats.tss import Tss
from tools.pythonlib.utils.dsv2sav import sav_to_dsv
from tools.pythonlib.formats.text_toh import text_to_bytes, bytes_to_text
import re
from itertools import chain
import io
from tqdm import tqdm
import struct
from ndspy import rom, codeCompression
from ndspy.code import loadOverlayTable, saveOverlayTable


class ToolsTOH():


    def __init__(self, project_file: Path, insert_mask: list[str], changed_only: bool = False) -> None:
        os.environ["PATH"] += os.pathsep + os.path.join( os.getcwd(), 'pythonlib', 'utils')
        base_path = project_file.parent

        if os.path.exists('programs_infos.json'):
            json_data = json.load(open('programs_infos.json'))
            self.desmume_path = Path(json_data['desmume_path'])
            self.save_size = json_data['save_size']


        self.folder_name = 'TOH'
        self.jsonTblTags = {}
        self.ijsonTblTags = {}
        with open(project_file, encoding="utf-8") as f:
            json_raw = json.load(f)

        self.paths: dict[str, Path] = {k: base_path / v for k, v in json_raw["paths"].items()}
        self.main_exe_name = json_raw["main_exe_name"]
        self.asm_file = json_raw["asm_file"]

        # super().__init__("TOR", str(self.paths["encoding_table"]), "Tales-Of-Rebirth")

        with open(self.paths["encoding_table"], encoding="utf-8") as f:
            json_raw = json.load(f)

        for k, v in json_raw.items():
            self.jsonTblTags[k] = {int(k2, 16): v2 for k2, v2 in v.items()}


        for k, v in self.jsonTblTags.items():
            if k in ['TAGS', 'TBL']:
                self.ijsonTblTags[k] = {v2:k2 for k2, v2 in v.items()}
            else:
                self.ijsonTblTags[k] = {v2: hex(k2).replace('0x', '').upper() for k2, v2 in v.items()}
        self.iTags = {v2.upper(): k2 for k2, v2 in self.jsonTblTags['TAGS'].items()}
        self.id = 1

        # byteCode
        self.story_byte_code = b"\xF8"
        self.story_struct_byte_code = [b'\x0E\x10\x00\x0C\x04', b'\x00\x10\x00\x0C\x04']
        self.VALID_VOICEID = [r'(VSM_\w+)', r'(VCT_\w+)', r'(S\d+)', r'(C\d+)']
        self.list_status_insertion: list[str] = ['Done']
        self.list_status_insertion.extend(insert_mask)
        self.COMMON_TAG = r"(<[\w/]+:?\w+>)"
        self.changed_only = changed_only
        self.repo_path = str(base_path)
        self.file_dict = {
            "skit": "data/fc/fcscr",
            "story": "data/m"
        }

    def extract_Iso(self, game_iso: Path) -> None:

        #Extract all the files
        print("Extracting the Iso's files...")
        extract_to = self.paths["original_files"]
        #self.clean_folder(extract_to)

        path = self.folder_name / extract_to
        args = ['ndstool', '-x', os.path.basename(game_iso),
                '-9', path/'arm9.bin',
                '-7', path/'arm7.bin',
                '-y9', path/'y9.bin',
                '-y7', path/'y7.bin',
                '-d', path/'data',
                '-y', path/'overlay',
                '-t', path/'banner.bin',
                '-h', path/'header.bin']

        wrk_dir = os.path.normpath(os.getcwd() + os.sep + os.pardir)
        subprocess.run(args, cwd=wrk_dir, stdout = subprocess.DEVNULL)

        #Update crappy arm9.bin to tinke's version
        with open(self.folder_name / extract_to / 'arm9.bin', "rb+") as f:
            data = f.read()
            f.seek(len(data) - 12)
            f.truncate()

        #Copy to patched folder
        #shutil.copytree(os.path.join('..', self.folder_name, self.paths["original_files"]), os.path.join('..', self.folder_name, self.paths["final_files"]), dirs_exist_ok=True)

    def make_iso(self, game_iso) -> None:
        #Clean old builds and create new one
        self.clean_builds(self.paths["game_builds"])

        # Set up new iso name and copy original iso in the folder

        n: datetime.datetime = datetime.datetime.now()
        new_iso = f"TalesofHearts_{n.year:02d}{n.month:02d}{n.day:02d}{n.hour:02d}{n.minute:02d}.nds"
        print(f'Making Iso {new_iso}...')
        self.new_iso = new_iso
        shutil.copy(game_iso, self.paths['game_builds'] / new_iso)

        path = self.folder_name / self.paths["final_files"]

        args = ['ndstool', '-c', new_iso,
                '-9', path / 'arm9.bin',
                '-7', path / 'arm7.bin',
                '-y9', path / 'y9.bin',
                '-y7', path / 'y7.bin',
                '-d', path / 'data',
                '-y', path / 'overlay',
                '-t', path / 'banner.bin',
                '-h', path / 'header.bin']

        subprocess.run(args, cwd=self.paths["game_builds"], stdout = subprocess.DEVNULL)

    def update_font(self):
        shutil.copyfile(self.paths['new_font'] / 'trialFont10.NFTR', self.paths['final_files'] / 'data' / 'trialFont10.NFTR')
        shutil.copyfile(self.paths['new_font'] / 'trialFont12.NFTR', self.paths['final_files'] / 'data' / 'trialFont12.NFTR')
        
    def update_arm9_size(self, game_iso:Path):

        with FileIO(game_iso, 'rb') as f:
            f.seek(0x28)
            load = f.read_uint32()
            f.seek(0x70)
            auto = f.read_uint32() - load

        compressed_arm9_path = self.paths['final_files'] / 'arm9.bin'
        decompressed_arm9_path = self.paths['temp_files'] / 'arm9/arm9.bin'
        arm9_comp_size = os.path.getsize(compressed_arm9_path)
        arm9_decomp_size = os.path.getsize(decompressed_arm9_path)
        with FileIO(compressed_arm9_path, 'r+b') as f:
            f.seek(auto - 4)
            offset = f.read_uint32() - load

            #1st value to update
            f.seek(offset)
            val1 = load + arm9_decomp_size - 0x18
            f.write_uint32(val1)

            #2nd value to update
            f.seek(offset + 1*4)
            val2 = load + arm9_decomp_size
            f.write_uint32(val2)

            #3rd value to update
            f.seek(offset + 5*4)
            val3 = load + arm9_comp_size
            f.write_uint32(val3)

            f.seek(0)
            return f.read()

    def update_overlays(self, romnds: rom, overlays_id: list):
        table = loadOverlayTable(romnds.arm9OverlayTable, lambda x, y: bytes())

        for id in overlays_id:
            ov3 = table[id]
            ov3.compressed = True

            self.compress_overlays()
            with open(self.paths['final_files'] / f'overlay/overlay_000{id}.bin', 'rb') as f:
                data_compressed = f.read()

            ov3.compressedSize = len(data_compressed)
            romnds.files[ov3.fileID] = data_compressed

        romnds.arm9OverlayTable = saveOverlayTable(table)



    def save_iso(self, game_iso:Path):

        self.clean_builds(self.paths["game_builds"])
        n: datetime.datetime = datetime.datetime.now()
        new_iso = f"TalesofHearts_{n.year:02d}{n.month:02d}{n.day:02d}{n.hour:02d}{n.minute:02d}.nds"
        print(f'Replacing files in new build: {new_iso}...')
        self.new_iso = new_iso

        romnds = rom.NintendoDSRom.fromFile(game_iso)
        path = Path(self.paths['final_files'])
        for file in path.rglob("*"):

            if file.is_file()  and 'patched_temp' not in str(file) and 'overlay' not in str(file) and file.stem != ".gitignore":

                with open(file, "rb") as f:
                    data = f.read()
                if file.stem == "arm9":
                    self.compress_arm9()
                    data = self.update_arm9_size(game_iso)
                    romnds.arm9 = data

                else:

                    i = file.parts.index('3_patched')
                    rem = file.parts[(i+1):]
                    path_file = '/'.join(rem)
                    path_file = path_file.replace('data/', '')
                    romnds.setFileByName(path_file, data)

        self.update_overlays(romnds, [0,3])
        romnds.saveToFile(self.paths['game_builds'] / self.new_iso)


    def decompress_arm9(self):

        #Copy the original file in a ARM9 folder
        new_arm9 = self.paths['extracted_files'] / 'arm9' / 'arm9.bin'
        new_arm9.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.paths['original_files'] / 'arm9.bin', new_arm9)

        #Decompress the file using blz
        print('Decompressing Arm9...')
        args = ['blz', '-d', new_arm9]
        subprocess.run(args, cwd=self.paths['tools'] / 'pythonlib' / 'utils', stdout = subprocess.DEVNULL)

    def compress_arm9(self):

        shutil.copy(self.paths['temp_files'] / 'arm9' / 'arm9.bin', self.paths['final_files'] / 'arm9.bin')

        #Copy the original file in a ARM9 folder

        #Compress the file using blz
        print('Compressing Arm9 and Overlays...')
        args = ['blz', '-en9', self.paths['final_files'] / 'arm9.bin']
        subprocess.run(args, cwd=self.paths['tools'] / 'pythonlib' / 'utils', stdout = subprocess.DEVNULL)

        # Update crappy arm9.bin to tinke's version
        #with open(self.paths['final_files'] / 'arm9.bin', "rb+") as f:
        #    data = f.read()
        #    f.seek(len(data) - 12)
            #f.truncate()


    def clean_folder(self, path: Path) -> None:
        target_files = list(path.iterdir())
        if len(target_files) != 0:
            print("Cleaning folder...")
            for file in target_files:
                if file.is_dir():
                    shutil.rmtree(file)
                elif file.name.lower() != ".gitignore":
                    file.unlink(missing_ok=False)

    def decompress_overlays(self):
        # Copy the original file in a ARM9 folder
        new_overlay = self.paths['extracted_files'] / 'overlay'
        new_overlay.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src=self.paths['original_files'] / 'overlay', dst=new_overlay, dirs_exist_ok=True)

        # Decompress the file using blz
        print('Decompressing Overlays...')
        args = ['blz', '-d', new_overlay / 'overlay*']
        subprocess.run(args, cwd= self.paths['tools'] / 'pythonlib' / 'utils', stdout = subprocess.DEVNULL)

    def compress_overlays(self):

        overlay_folder = self.paths['final_files'] / 'overlay'
        overlay_folder.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.paths['temp_files'] / 'overlay' / 'overlay_0003.bin', overlay_folder / 'overlay_0003.bin')
        args = ['blz', '-en', overlay_folder / 'overlay_0003.bin']
        subprocess.run(args, cwd=self.paths['tools'] / 'pythonlib' / 'utils', stdout=subprocess.DEVNULL)

    def adjusted_y9(self, overlay_name):

        compressed_size = os.path.getsize(self.paths['final_files'] / 'overlay' / overlay_name)

        with FileIO(self.paths['final_files'] / 'y9.bin', 'rb') as f:
            data = f.read()
            data[0x1C:0x1E] = compressed_size.to_bytes(3, 'little')
            return data


    def clean_builds(self, path: Path) -> None:
        target_files = sorted(list(path.glob("*.nds")), key=lambda x: x.name)[:-4]
        if len(target_files) != 0:
            print("Cleaning builds folder...")
            for file in target_files:
                print(f"Deleting {str(file.name)}...")
                file.unlink()

    def update_save_file(self, desmume_path:Path, saved_file_name:str):

        if saved_file_name != '':
            destination = desmume_path / 'Battery' / saved_file_name
            shutil.copy(self.paths['saved_files'] / saved_file_name, destination)

            if saved_file_name.endswith('.sav'):
                self.convert_sav_to_dsv(desmume_path, saved_file_name)

            else:
                new_saved_name = f"{self.new_iso.split('.')[0]}.dsv"
                os.rename(destination, destination.parent / new_saved_name)

    def convert_sav_to_dsv(self, desmume_path:Path, saved_file_name:str):
        trimSize = 122
        footer = [124, 60, 45, 45, 83, 110, 105, 112, 32, 97, 98, 111, 118, 101, 32, 104,
                  101, 114, 101, 32, 116, 111, 32, 99, 114, 101, 97, 116, 101, 32, 97, 32,
                  114, 97, 119, 32, 115, 97, 118, 32, 98, 121, 32, 101, 120, 99, 108, 117,
                  100, 105, 110, 103, 32, 116, 104, 105, 115, 32, 68, 101, 83, 109, 117, 77,
                  69, 32, 115, 97, 118, 101, 100, 97, 116, 97, 32, 102, 111, 111, 116, 101,
                  114, 58, 0, 0, 1 ,0 , 0, 0, 1, 0, 3, 0, 0, 0, 2, 0, 0, 0, 0, 0, 1, 0, 0,
                  0, 0, 0, 124, 45, 68, 69, 83, 77, 85, 77, 69, 32, 83, 65, 86, 69, 45, 124]

        sav_file = desmume_path / 'Battery' / saved_file_name
        destination = desmume_path / 'Battery' / f"{self.new_iso.split('.')[0]}.dsv"
        print(destination)
        binary = bytearray(footer)
        with open(sav_file, 'rb') as inFile:
            with open(destination, 'wb') as outFile:
                contents = inFile.read()
                outFile.write(contents)
                outFile.write(binary)
        os.remove(sav_file)

    def get_style_pointers(self, file: FileIO, ptr_range: tuple[int, int], base_offset: int, style: str) -> tuple[
        list[int], list[int]]:

        file.seek(ptr_range[0])
        pointers_offset: list[int] = []
        pointers_value: list[int] = []
        split: list[str] = [ele for ele in re.split(r'([PT])|(\d+)', style) if ele]

        while file.tell() < ptr_range[1]:
            for step in split:
                if step == "P":
                    off = file.read_uint32()
                    if base_offset != 0 and off == 0: continue

                    if file.tell() - 4 < ptr_range[1]:
                        pointers_offset.append(file.tell() - 4)
                        pointers_value.append(off - base_offset)
                elif step == "T":
                    off = file.tell()
                    pointers_offset.append(off)
                    pointers_value.append(off)
                else:
                    file.read(int(step))

        return pointers_offset, pointers_value

    def create_Node_XML(self, root, list_informations, section, entry_type:str, max_len = 0, ) -> None:
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = section

        for text, pointer_offset, emb in list_informations:
            self.create_entry(strings_node, pointer_offset, text, entry_type, -1, "")
            #self.create_entry(strings_node, pointers_offset, text, emb, max_len)
    def extract_all_menu(self, keep_translations=False) -> None:
        #xml_path = self.paths["menu_xml"]
        xml_path = self.paths["menu_original"]
        xml_path.mkdir(exist_ok=True)

        # Read json descriptor file
        with open(self.paths["menu_table"], encoding="utf-8") as f:
            menu_json = json.load(f)

        for entry in tqdm(menu_json, desc='Extracting Menu Files'):

            if entry["friendly_name"] == "Arm9" or entry["friendly_name"].startswith("Overlay"):
                file_path = self.paths["extracted_files"] / entry["file_path"]
            else:
                file_path = self.paths["original_files"] / entry["file_path"]

            with FileIO(file_path, "rb") as f:
                xml_data = self.extract_menu_file(entry, f, keep_translations)

            with open(xml_path / (entry["friendly_name"] + ".xml"), "wb") as xmlFile:
                xmlFile.write(xml_data)

            self.id = 1
    def extract_menu_file(self, file_def, f: FileIO, keep_translations=False) -> bytes:

        base_offset = file_def["base_offset"]
        xml_root = etree.Element("MenuText")

        for section in file_def['sections']:
            max_len = 0
            pointers_offset  = []
            pointers_value = []
            if "pointers_start" in section.keys():
                pointers_start = int(section["pointers_start"])
                pointers_end = int(section["pointers_end"])

                # Extract Pointers list out of the file
                pointers_offset, pointers_value = self.get_style_pointers(f, (pointers_start, pointers_end), base_offset,
                                                                          section['style'])
            if 'pointers_alone' in section.keys():
                for ele in section['pointers_alone']:
                    f.seek(ele, 0)
                    pointers_offset.append(f.tell())
                    off = f.read_uint32() - base_offset
                    pointers_value.append(off)

            #print([hex(pointer_off) for pointer_off in pointers_offset])
            # Make a list, we also merge the emb pointers with the
            # other kind in the case they point to the same text
            temp = dict()
            for off, val in zip(pointers_offset, pointers_value):
                text, buff = bytes_to_text(f, val)
                temp.setdefault(text, dict()).setdefault("ptr", []).append(off)

            # Remove duplicates
            list_informations = [(k, str(v['ptr'])[1:-1], v.setdefault('emb', None)) for k, v in temp.items()]

            # Build the XML Structure with the information
            if 'style' in section.keys() and section['style'][0] == "T": max_len = int(section['style'][1:])
            self.create_Node_XML(xml_root, list_informations, section['section'], "String", max_len)

        if keep_translations:
            self.copy_translations_menu(root_original=xml_root, translated_path=self.paths['menu_xml'] / f"{file_def['friendly_name']}.xml")

        # Write to XML file
        return etree.tostring(xml_root, encoding="UTF-8", pretty_print=True)

    def parse_entry(self, xml_node):

        jap_text = xml_node.find('JapaneseText').text
        eng_text = xml_node.find('EnglishText').text
        status = xml_node.find('Status').text
        notes = xml_node.find('Notes').text

        final_text = eng_text or jap_text or ''
        return jap_text, eng_text, final_text, status, notes

    def copy_translations_menu(self, root_original, translated_path: Path):

        if translated_path.exists():

            original_entries = {entry_node.find('JapaneseText').text: (section.find('Section').text,) +
                                                                       self.parse_entry(entry_node) for section in
                                root_original.findall('Strings') for entry_node in section.findall('Entry')}

            tree = etree.parse(translated_path)
            root_translated = tree.getroot()
            translated_entries = {entry_node.find('JapaneseText').text: (section.find('Section').text,) +
                                                   self.parse_entry(entry_node) for section in
             root_translated.findall('Strings') for entry_node in section.findall('Entry')}


            for entry_node in root_original.iter('Entry'):

                jap_text = entry_node.find('JapaneseText').text

                if jap_text in translated_entries:

                    translated = translated_entries[jap_text]

                    if translated_entries[jap_text][2] is not None:
                        entry_node.find('EnglishText').text = translated_entries[jap_text][2]
                        entry_node.find('Status').text = translated_entries[jap_text][4]
                        entry_node.find('Notes').text = translated_entries[jap_text][5]

                else:
                    t = 2
                    #print(f'String: {jap_text} was not found in translated XML')

            #[print(f'{entry} was not found in original') for entry, value in translated_entries.items() if entry not in original_entries and entry is not None]

    def unpack_menu_files(self):
        base_path = self.paths['extracted_files'] / 'data/menu'/ 'monsterbook'
        fps4 = Fps4(detail_path=self.paths['original_files'] / 'data/menu' / 'monsterbook' / 'EnemyIcon.dat',
                    header_path=self.paths['original_files'] / 'data/menu' / 'monsterbook' / 'EnemyIcon.b')
        fps4.extract_files(base_path, decompressed=False)

        for file in fps4.files:
            file_path = self.paths['extracted_files'] / 'data/menu/monsterbook/' / file.name
            enemy_fps4 = Fps4(header_path=file_path)
            print(file_path.with_suffix(''))
            enemy_fps4.extract_files(file_path.with_suffix(''), decompressed=True)


    def pack_all_menu(self) -> None:
        xml_path = self.paths["menu_xml"]

        # Read json descriptor file
        with open(self.paths["menu_table"], encoding="utf-8") as f:
            menu_json = json.load(f)

        for entry in tqdm(menu_json, total=len(menu_json), desc='Inserting Menu Files'):


            if entry["friendly_name"] in ['Arm9', 'Consumables', 'Sorma Skill', 'Outline', 'Overlay 0', 'Overlay 3', 'Soma Data', 'Strategy', 'Battle Memo']:
                # Copy original files

                orig = self.paths["extracted_files"] / entry["file_path"]
                if not orig.exists():
                    orig = self.paths["original_files"] / entry["file_path"]

                dest = self.paths["temp_files"] / entry["file_path"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(orig, dest)

                base_offset = entry["base_offset"]
                pools: list[list[int]] = [[x[0], x[1] - x[0]] for x in entry["safe_areas"]]
                pools.sort(key=lambda x: x[1])

                with open(xml_path / (entry["friendly_name"] + ".xml"), "r", encoding='utf-8') as xmlFile:
                    root = etree.fromstring(xmlFile.read(), parser=etree.XMLParser(recover=True))

                with open(dest, "rb") as f:
                    file_b = f.read()

                with FileIO(file_b, "wb") as f:
                    self.pack_menu_file(root, pools, base_offset, f,entry['pad'])

                    f.seek(0)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest, "wb") as g:
                        g.write(f.read())

                #Copy in the patched folder
                if entry['friendly_name'] != "Arm9":
                    (self.paths['final_files'] / entry['file_path']).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src=dest,
                                dst=self.paths['final_files'] / entry['file_path'])
                else:
                    shutil.copyfile(src=dest,
                                    dst=self.paths['final_files'] / 'arm9.bin')

    def pack_menu_file(self, root, pools: list[list[int]], base_offset: int, f: FileIO, pad=False) -> None:

        if root.find("Strings").find("Section").text == "Arm9":
            min_seq = 400
            entries = [ele for ele in root.iter("Entry") if
                       ele.find('PointerOffset').text not in ['732676', '732692', '732708']
                       and int(ele.find('Id').text) <= min_seq]
        else:
            entries = root.iter("Entry")

        for line in entries:
            hi = []
            lo = []
            flat_ptrs = []

            p = line.find("EmbedOffset")
            if p is not None:
                hi = [int(x) - base_offset for x in p.find("hi").text.split(",")]
                lo = [int(x) - base_offset for x in p.find("lo").text.split(",")]

            poff = line.find("PointerOffset")
            if poff.text is not None:
                flat_ptrs = [int(x) for x in poff.text.split(",")]

            mlen = line.find("MaxLength")
            if mlen is not None:
                max_len = int(mlen.text)
                f.seek(flat_ptrs[0])
                text_bytes = self.get_node_bytes(line,pad) + b"\x00"
                if len(text_bytes) > max_len:
                    tqdm.write(
                        f"Line id {line.find('Id').text} ({line.find('JapaneseText').text}) too long, truncating...")
                    f.write(text_bytes[:max_len - 1] + b"\x00")
                else:
                    f.write(text_bytes + (b"\x00" * (max_len - len(text_bytes))))
                continue

            text_bytes = self.get_node_bytes(line,pad) + b"\x00"

            l = len(text_bytes)
            for pool in pools:

                if l <= pool[1]:
                    str_pos = pool[0]
                    #print(f'offset in pool: {hex(pool[0])}')
                    pool[0] += l;
                    pool[1] -= l

                    break
            else:
                print("Ran out of space")
                raise ValueError(f'Ran out of space in file: {root.find("Strings").find("Section").text}')

            f.seek(str_pos)
            f.write(text_bytes)
            virt_pos = str_pos + base_offset
            for off in flat_ptrs:
                f.write_uint32_at(off, virt_pos)

            for _h, _l in zip(hi, lo):
                val_hi = (virt_pos >> 0x10) & 0xFFFF
                val_lo = (virt_pos) & 0xFFFF

                # can't encode the lui+addiu directly
                if val_lo >= 0x8000: val_hi += 1

                f.write_uint16_at(_h, val_hi)
                f.write_uint16_at(_l, val_lo)


    def get_node_bytes(self, entry_node, pad=False) -> bytes:

        # Grab the fields from the Entry in the XML
        #print(entry_node.find("JapaneseText").text)
        status = entry_node.find("Status").text
        japanese_text = entry_node.find("JapaneseText").text
        english_text = entry_node.find("EnglishText").text

        # Use the values only for Status = Done and use English if non-empty
        final_text = ''
        if (status in self.list_status_insertion):
            final_text = english_text or ''
        else:
            final_text = japanese_text or ''

        voiceid_node = entry_node.find("VoiceId")

        if voiceid_node is not None:
            final_text = f'<{voiceid_node.text}>' + final_text

        # Convert the text values to bytes using TBL, TAGS, COLORS, ...
        bytes_entry = text_to_bytes(final_text)

        #Pad with 00
        if pad:
            rest = 4 - len(bytes_entry) % 4 - 1
            bytes_entry += (b'\x00' * rest)

        return bytes_entry

    def extract_all_skits(self, keep_translations=False):
        type = 'skit'
        base_path = self.paths['extracted_files'] / self.file_dict[type]
        base_path.mkdir(parents=True, exist_ok=True)
        fps4 = Fps4(detail_path=self.paths['original_files'] / 'data' / 'fc' / 'fcscr.dat',
                    header_path=self.paths['original_files'] / 'data' / 'fc' / 'fcscr.b')
        fps4.extract_files(destination_path=base_path, copy_path=self.paths['temp_files'] / self.file_dict['skit'], decompressed=True)

        self.paths['skit_xml'].mkdir(parents=True, exist_ok=True)
        self.paths['skit_original'].mkdir(parents=True, exist_ok=True)
        for tss_file in tqdm(base_path.iterdir(), desc='Extracting Skits Files...'):
            tss_obj = Tss(tss_file, list_status_insertion=self.list_status_insertion)
            if len(tss_obj.struct_dict) > 0:
                tss_obj.extract_to_xml(original_path=self.paths['skit_original'] / tss_file.with_suffix('.xml').name,
                                       translated_path=self.paths['skit_xml'] / tss_file.with_suffix('.xml').name,
                                       keep_translations=keep_translations)

    def pack_tss(self, destination_path:Path, xml_path:Path):
        tss = Tss(path=destination_path,
                  list_status_insertion=self.list_status_insertion)

        tss.pack_tss_file(destination_path=destination_path,
                          xml_path=xml_path)

    def pack_all_skits(self):
        type = 'skit'

        fps4 = Fps4(detail_path=self.paths['original_files'] / 'data' / 'fc' / 'fcscr.dat',
                    header_path=self.paths['original_files'] / 'data' / 'fc' / 'fcscr.b')

        xml_list, archive_list = self.find_changes('skit')

        #Repack TSS files
        for archive in tqdm(archive_list, total=len(archive_list), desc="Inserting Skits Files..."):
            end_name = f"{self.file_dict[type]}/{archive}.FCBIN"
            src = self.paths['extracted_files'] / end_name
            tss_path = self.paths['temp_files'] / end_name
            shutil.copy(src=src,
                        dst=tss_path)
            self.pack_tss(destination_path=tss_path,
                          xml_path=self.paths['skit_xml'] / f'{archive}.xml')

            args = ['lzss', '-evn', tss_path]
            subprocess.run(args, stdout=subprocess.DEVNULL)

        #Repack FPS4 archive
        final_path = self.paths['final_files'] / 'data' / 'fc'
        final_path.mkdir(parents=True, exist_ok=True)
        fps4.pack_file(updated_file_path=self.paths['temp_files'] / self.file_dict[type],
                       destination_folder=final_path)


    def pack_mapbin_story(self, file_name, type):
        mapbin_folder = self.paths['temp_files'] / self.file_dict[type] / file_name

        fps4_mapbin = Fps4(detail_path=self.paths['extracted_files'] / self.file_dict[type] / f'{file_name}.MAPBIN',
                           header_path=self.paths['extracted_files'] / self.file_dict[type] / f'{file_name}.B')

        fps4_mapbin.pack_fps4_type1(updated_file_path=mapbin_folder,
                                    destination_folder=self.paths['temp_files'] / self.file_dict[type])
    def pack_all_story(self):
        type = 'story'
        # Copy original TSS files in the "updated" folder
        dest = self.paths['temp_files'] / self.file_dict[type]

        #Repack all the TSS that need to be updated based on status changed
        xml_list, archive_list = self.find_changes('story')

        if len(xml_list) > 0:
            for xml_path in tqdm(xml_list, total=len(xml_list), desc='Inserting Story Files'):

                if os.path.exists(xml_path):
                    archive_name = xml_path.stem if not xml_path.stem.endswith('P') else xml_path.stem[0:-1]
                    end_name = f"{self.file_dict['story']}/{archive_name}/{xml_path.stem}.SCP"
                    src = self.paths['extracted_files'] / end_name
                    tss_path = self.paths['temp_files'] / end_name
                    shutil.copy(src=src,
                                dst=tss_path)
                    self.pack_tss(destination_path=tss_path,
                                  xml_path=xml_path)

                    args = ['lzss', '-evn', tss_path]
                    subprocess.run(args, stdout = subprocess.DEVNULL)

            # Find all the xmls that has changed recently
            for archive in archive_list:
                self.pack_mapbin_story(archive, type)

            folder = 'm'
            base_path = self.paths['extracted_files'] / 'data' / folder
            (self.paths['final_files'] / self.file_dict[type]).mkdir(parents=True, exist_ok=True)
            fps4_m = Fps4(detail_path=self.paths['original_files'] / self.file_dict['story'] / f'{folder}.dat',
                        header_path=self.paths['original_files'] / self.file_dict['story'] / f'{folder}.b')
            fps4_m.pack_fps4_type1(updated_file_path=self.paths['temp_files'] / self.file_dict[type],
                                   destination_folder=self.paths['final_files'] / self.file_dict[type])

    def find_changes(self, type):

        xml_list = []
        archive_list = []
        for xml_path in [path for path in self.paths[f'{type}_xml'].iterdir() if 'git' not in path.name]:
            tree = etree.parse(xml_path)
            root = tree.getroot()
            entries_translated = [entry for entry in root.iter('Entry') if entry.find('Status').text in self.list_status_insertion]


            if len(entries_translated) > 0:
                archive_name = xml_path.stem if not xml_path.stem.endswith('P') else xml_path.stem[0:-1]
                xml_list.append(xml_path)
                archive_list.append(archive_name)

        archive_list = list(set(archive_list))

        return xml_list, archive_list

    def extract_tss(self, tss_file:Path, file_type:str, keep_translations=False):
        tss_obj = Tss(path=tss_file, list_status_insertion=self.list_status_insertion)

        if (len(tss_obj.struct_dict) > 0) or (len(tss_obj.string_list) > 0):
            original_path = self.paths[f'{file_type}_original'] / tss_file.with_suffix('.xml').name
            translated_path = self.paths[f'{file_type}_xml'] / tss_file.with_suffix('.xml').name
            tss_obj.extract_to_xml(original_path= original_path,
                                       translated_path=translated_path,
                                       keep_translations=keep_translations)


    def extract_all_story(self, extract_XML=False):
        folder = 'm'
        base_path = self.paths['extracted_files'] / 'data' / folder

        fps4 = Fps4(detail_path=self.paths['original_files'] / 'data' / folder / f'{folder}.dat',
                    header_path=self.paths['original_files'] / 'data' / folder / f'{folder}.b')
        copy_path = self.paths['temp_files'] / self.file_dict['story']
        fps4.extract_files(destination_path=base_path, copy_path=copy_path)

        self.paths['story_xml'].mkdir(parents=True, exist_ok=True)
        self.paths['story_original'].mkdir(parents=True, exist_ok=True)
        scp_files = [file for file in base_path.iterdir() if file.suffix == '.MAPBIN']
        for file in tqdm(scp_files, total=len(scp_files), desc=f"Extracting Story Files"):


            file_header = file.with_suffix('.B')
            fps4_tss = Fps4(detail_path=file, header_path=file_header)
            folder_path = file.with_suffix('')
            folder_path.mkdir(parents=True, exist_ok=True)
            fps4_tss.extract_files(destination_path=folder_path, copy_path=copy_path / file.stem, decompressed=True)

            #Load the tss file
            for tss_file in [file_path for file_path in folder_path.iterdir() if file_path.suffix == '.SCP']:
                self.extract_tss(tss_file, 'story')




    def create_entry(self, strings_node, pointer_offset, text, entry_type, speaker_id, unknown_pointer):

        # Add it to the XML node
        entry_node = etree.SubElement(strings_node, "Entry")
        etree.SubElement(entry_node, "PointerOffset").text = str(pointer_offset).replace(' ', '')
        text_split = re.split(self.COMMON_TAG, text)

        if len(text_split) > 1 and any(possible_value in text for possible_value in self.VALID_VOICEID):
            etree.SubElement(entry_node, "VoiceId").text = text_split[1]
            etree.SubElement(entry_node, "JapaneseText").text = ''.join(text_split[2:])
        else:
            etree.SubElement(entry_node, "JapaneseText").text = text

        etree.SubElement(entry_node, "EnglishText")
        etree.SubElement(entry_node, "Notes")

        if entry_type == "Struct":
            etree.SubElement(entry_node, "StructId").text = str(self.struct_id)
            etree.SubElement(entry_node, "SpeakerId").text = str(speaker_id)

        etree.SubElement(entry_node, "Id").text = str(self.id)
        etree.SubElement(entry_node, "Status").text = "To Do"
        self.id += 1
    def extract_from_string(self, f, strings_offset, pointer_offset, text_offset, root):

        f.seek(text_offset, 0)
        japText, buff = bytes_to_text(f, text_offset)
        self.create_entry(root, pointer_offset, japText, "Other Strings", -1, "")



    def text_to_bytes(self, text):
        multi_regex = (self.HEX_TAG + "|" + self.COMMON_TAG + r"|(\n)")
        tokens = [sh for sh in re.split(multi_regex, text) if sh]

        output = b''
        for t in tokens:
            # Hex literals
            if re.match(self.HEX_TAG, t):
                output += struct.pack("B", int(t[1:3], 16))

            # Tags
            elif re.match(self.COMMON_TAG, t):
                tag, param, *_ = t[1:-1].split(":") + [None]

                if tag == "icon":
                    output += struct.pack("B", self.ijsonTblTags["TAGS"].get(tag))
                    output += b'\x28' + struct.pack('B', int(param)) + b'\x29'

                elif any(re.match(possible_value, tag)  for possible_value in self.VALID_VOICEID):
                    output += b'\x09\x28' + tag.encode("cp932") + b'\x29'

                elif tag == "Bubble":
                    output += b'\x0C'

                else:
                    if tag in self.ijsonTblTags["TAGS"]:
                        output += struct.pack("B", self.ijsonTblTags["TAGS"][tag])
                        continue

                    for k, v in self.ijsonTblTags.items():
                        if tag in v:
                            if k in ['NAME', 'COLOR']:
                                output += struct.pack('B',self.iTags[k]) + b'\x28' + bytes.fromhex(v[tag]) + b'\x29'
                                break
                            else:
                                output += b'\x81' + bytes.fromhex(v[tag])

            # Actual text
            elif t == "\n":
                output += b"\x0A"
            else:
                for c in t:
                    if c in self.PRINTABLE_CHARS or c == "\u3000":
                        output += c.encode("cp932")
                    else:

                        if c in self.ijsonTblTags["TBL"].keys():
                            b = self.ijsonTblTags["TBL"][c].to_bytes(2, 'big')
                            output += b
                        else:
                            output += c.encode("cp932")



        return output
