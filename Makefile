CURRENT_VERSION=$(shell cat __init__.py | cut -d "'" -f 2)
DOCKER_IMAGE_NAME=dataesr/pydref
GHCR_IMAGE_NAME=ghcr.io/$(DOCKER_IMAGE_NAME)

docker-build:
	@echo Building a new docker image
	docker build -t $(GHCR_IMAGE_NAME):$(CURRENT_VERSION) -t $(GHCR_IMAGE_NAME):latest .
	@echo Docker image built

docker-push:
	@echo Pushing a new docker image
	docker push -a $(GHCR_IMAGE_NAME)
	@echo Docker image pushed

release:
	echo "__version__ = '$(VERSION)'" > __init__.py
	git commit -am '[release] version $(VERSION)'
	git tag $(VERSION)
	@echo If everything is OK, you can push with tags i.e. git push origin main --tags

