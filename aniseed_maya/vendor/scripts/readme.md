# Vendoring

Vendoring is a practice of embedding or packaging up dependencies 
within a module to make it more portable. However it is not a good
practice in a production environment.

Aniseed is deployed with a vendor folder to make it easy for users
who are not comfortable with python. That way they can download aniseed
and start using it immediately.

### Single User

If you are a single user purely using Aniseed to build rigs then
leaving the vendored libraries is most likely the best and easiest
solution. Therefore you need not make any changes. and run Aniseed
as it is.

### Production Environment

If you're in an environment where there are a lot of other python 
modules and tools being used then you should consider moving these
out of the vendor folder and placing them in a managed location. That
way you will not risk having duplicate python modules which need
managing.

Note that the following vendored modules can be grabbed from pypi:

* factories
* qtility
* scribble
* signalling
* xstack
* blackout
* Qt

The following are direct from github (MIT License)

* crosswalk
* snappy
