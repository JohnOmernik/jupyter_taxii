# jupyter_taxii
A module to help interaction with Jupyter Notebooks and Taxii Servers

------
This is a python module that helps to connect Jupyter Notebooks to various datasets. 
It's based on (and requires) https://github.com/JohnOmernik/jupyter_integration_base 



## Initialization 
----

### Example Inits

#### Embedded mode using qgrid
```
from taxii_core import Taxii
ipy = get_ipython()
mytaxii = Taxii(ipy, debug=False)
ipy.register_magics(mytaxii)
```

