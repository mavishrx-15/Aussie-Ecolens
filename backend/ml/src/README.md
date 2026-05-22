# How to use

import WildlifeModelService from model_service.py and then:

``` python
model_service = WildlifeModelService()
result = model_service.process_image(image_path)
```

it should return:
- file name
- all detections with their respective bounding boxes, predicted label and confidence value
- tags with associated count

# How to test model
in /src:
``` bash
python test/batch_test.py
```
or
```bash
python test/single_test.py
```