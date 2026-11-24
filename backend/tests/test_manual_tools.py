"""Manual controls: pixel behaviour, geometry and original preservation."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from PIL import Image
from pydantic import ValidationError
from app.config import Settings
from app.schemas.images import Adjustments, Crop
from app.services.images import render
from app.services.manual import tone_table, geometry_size

NEUTRAL=dict(brightness=100,contrast=100,saturation=100,warmth=0,sharpness=0,vignette=0)

class ManualToolsTests(unittest.TestCase):
    def test_neutral_and_exposure_tone_mapping(self):
        self.assertEqual(tone_table(),list(range(256)))
        self.assertEqual(tone_table(exposure=1)[64],128)
        self.assertGreater(tone_table(shadows=70)[32],32)
        self.assertLess(tone_table(highlights=-70)[220],220)
        self.assertEqual(tone_table(ambience=100)[0],0)
        self.assertEqual(tone_table(ambience=100)[255],255)

    def test_rotation_flip_and_straightening_preserve_source(self):
        settings=Settings(_env_file=None,database_url='postgresql://app:password@localhost/test?sslmode=require')
        with TemporaryDirectory() as folder:
            source=Path(folder)/'source.png'
            image=Image.new('RGB',(80,40),(10,20,30));image.paste((250,0,0),(0,0,40,40));image.save(source)
            original=source.read_bytes()
            for rotation in (0,90,180,270):
                for angle in (-15,0,15):
                    adjustments=Adjustments(**NEUTRAL,rotation=rotation,straighten=angle,flip_horizontal=True)
                    result=Image.open(BytesIO(render(source,adjustments,settings,preview=False)))
                    self.assertEqual(result.size,geometry_size(80,40,adjustments))
                    self.assertEqual(source.read_bytes(),original)
            result=Image.open(BytesIO(render(source,Adjustments(**NEUTRAL,rotation=90),settings,preview=False,crop=Crop(x=0,y=0,width=40,height=20),original_size=(80,40))))
            self.assertEqual(result.size,(20,40))

    def test_request_validation_and_old_settings(self):
        self.assertEqual(Adjustments(**NEUTRAL).rotation,0)
        for patch in ({'rotation':45},{'exposure':4},{'straighten':31},{'shadows':101},{'structure':-1}):
            with self.assertRaises(ValidationError):Adjustments(**NEUTRAL,**patch)

if __name__=='__main__':unittest.main()
