rm -rf ./dist
rm -rf ./stextras.egg-info
python3 ./build_tools/make_readme.py
pandoc README.md --from markdown --to rst -s -o README.rst
cd docs
sphinx-apidoc -o ./api ../streamlitextras
make clean && make html
cd ..
python3 -m build && python3 -m twine upload --repository testpypi dist/*
