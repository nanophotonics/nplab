sphinx-apidoc -f -o ./docs ./nplab
cd docs
make html
make latexpdf
