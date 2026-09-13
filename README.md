Just resize:
{ "resize": { "width": 300, "height": 200 } }

Crop then rotate:
{ "crop": { "left": 0, "top": 0, "right": 400, "bottom": 300 }, "rotate": 90 }

Grayscale + convert to PNG:
{ "grayscale": true, "format": "PNG" }

Sepia + compress as JPEG:
{ "sepia": true, "format": "JPEG", "quality": 60 }

Flip + mirror combined:
{ "flip": true, "mirror": true }