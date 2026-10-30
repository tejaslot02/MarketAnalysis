.PHONY: install run scrape-nifty scrape-banknifty market-status test clean

install:
	pip install -r requirements.txt

run:
	python main.py -s NIFTY

scrape-nifty:
	python main.py -s NIFTY

scrape-banknifty:
	python main.py -s BANKNIFTY

market-status:
	python main.py --market-status

test:
	pytest tests/ -v

clean:
	rm -rf __pycache__ */__pycache__ tests/__pycache__ .pytest_cache
