# Scripts

## Pre

- [resume.py](./resume.py): use it for checking if there are complete days inside LiteMe datasets
- [features.py](./features.py): use it for features extraction of LiteMe datasets.
- [clustering.py](./clustering.py): use it for trying to group by clusters
- [generate_samples.py](./generate_samples.py): use it for extract complete day files from LiteMe datasets

## Running

- [experiment.py](./experiment.py): this is the main file for metrics analysis using all the datasets
- [main.py](./main.py): use it for single compression and result analysis

## Pos

- [joint.py](./analysis/src/joint.py) 
python3 analysis/src/joint.py --dataset experiments/resultados.csv --algoritmo dct --target_cr 80 --janela 720