"""Run processing regressions against the code and font inside the actual EXE."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from PyInstaller.archive.readers import CArchiveReader
import test_processor


def verify(exe='dist/ThanhVi.exe'):
    archive = CArchiveReader(exe)
    code = archive.open_embedded_archive('PYZ.pyz').extract('processor')
    entries = {key.replace('\\','/'): key for key in archive.toc}
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
        root = Path(td)
        for name in ('DancingScript.ttf','OFL.txt'):
            key = 'assets/fonts/'+name
            data = archive.extract(entries[key])
            assert data == (Path(__file__).parent/key).read_bytes(), 'Bundled font/license mismatch'
            dest = root/key
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(data)
        frozen = types.ModuleType('processor_frozen')
        frozen.__file__ = str(root/'processor.py')
        with patch.object(sys,'_MEIPASS',str(root),create=True):
            exec(code,frozen.__dict__)
        assert 'logo_mask' in frozen.clean_logo.__code__.co_names, 'Outdated processor in EXE'
        assert 'Thanh Vị' in frozen.sign.__code__.co_consts, 'Outdated signature in EXE'
        assert 'SIGNATURE_FONT' in frozen.sign.__code__.co_names, 'Bundled font is not used'
        with patch.object(test_processor,'p',frozen):
            suite=unittest.defaultTestLoader.loadTestsFromModule(test_processor)
            result=unittest.TextTestRunner(verbosity=1).run(suite)
            if not result.wasSuccessful():
                raise SystemExit(1)
    print('EXE code, bundled font and regressions verified')


if __name__ == '__main__':
    verify(sys.argv[1] if len(sys.argv)>1 else 'dist/ThanhVi.exe')
