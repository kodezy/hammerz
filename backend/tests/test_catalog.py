import httpx

from tests.conftest import auth_headers


def test_search_maps_object(client, seller_token, respx_mock):
    respx_mock.get("https://collectionapi.metmuseum.org/public/collection/v1.1/search").mock(
        return_value=httpx.Response(200, json={"objectIDs": [436535], "total": 1})
    )
    respx_mock.get("https://collectionapi.metmuseum.org/public/collection/v1/objects/436535").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectID": 436535,
                "title": "Wheat Field with Cypresses",
                "primaryImage": "https://example.com/img.jpg",
                "isPublicDomain": True,
            },
        )
    )
    r = client.get("/api/v1/catalog/search?q=wheat", headers=auth_headers(seller_token))
    assert r.status_code == 200
    assert r.json()["items"][0]["external_id"] == "436535"


def test_search_strips_html_in_title(client, seller_token, respx_mock):
    respx_mock.get("https://collectionapi.metmuseum.org/public/collection/v1.1/search").mock(
        return_value=httpx.Response(200, json={"objectIDs": [123], "total": 1})
    )
    respx_mock.get("https://collectionapi.metmuseum.org/public/collection/v1/objects/123").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectID": 123,
                "title": "Ceremonial Armors for Man (<i>Dingjia</i>) and Horse",
                "primaryImage": "https://example.com/img.jpg",
                "isPublicDomain": True,
            },
        )
    )
    r = client.get("/api/v1/catalog/search?q=armor", headers=auth_headers(seller_token))
    assert r.status_code == 200
    assert r.json()["items"][0]["title"] == "Ceremonial Armors for Man (Dingjia) and Horse"


def test_bidder_forbidden(client, bidder_token):
    r = client.get("/api/v1/catalog/search?q=wheat", headers=auth_headers(bidder_token))
    assert r.status_code == 403


def test_met_timeout_503(client, seller_token, respx_mock):
    from src.modules import catalog as catalog_module

    catalog_module._cache.clear()
    respx_mock.get("https://collectionapi.metmuseum.org/public/collection/v1.1/search").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    r = client.get("/api/v1/catalog/search?q=timeout-only", headers=auth_headers(seller_token))
    assert r.status_code == 503
    assert r.json()["code"] == "CATALOG_UNAVAILABLE"
