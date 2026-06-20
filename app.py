"""
FastAPI app for Hugging Face Space deployment.
Exposes Layer Crawler ETL Engine endpoints for underwriting and verification.
"""

import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile
import shutil

from layer_crawler_etl import (
    SourceRegistry,
    CodeCrawler,
    DependencyCrawler,
    LicenseCrawler,
    SecurityCrawler,
    TestBuildCrawler,
    BrowserRuntimeCrawler,
    Extractor,
    Transformer,
    Loader,
    Scorer,
    ActionEngine,
    JobQueue,
    QueueBackend,
    CrawlerWorker
)
from underwriting_endpoints import (
    FEMAClient,
    PlaidClient,
    OFACClient,
    SanctionsComplianceEngine,
    SmartyClient,
    FirstStreetClient,
    OCRProcessor
)
from receipts import ReceiptGenerator, ReceiptLedger, ReceiptVerifier
from proofbook_integration import UnderwritingProofBook

# Initialize FastAPI app
app = FastAPI(
    title="Layer Crawler ETL Engine",
    description="4-layer crawler, ETL, scoring, and action engine for software verification and underwriting",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
source_registry = SourceRegistry()
job_queue = JobQueue(backend=QueueBackend.MEMORY)
worker = CrawlerWorker(job_queue, source_registry)
receipt_generator = ReceiptGenerator("Layer Crawler ETL Engine - HF Space")
receipt_ledger = ReceiptLedger()
receipt_verifier = ReceiptVerifier()
proofbook = UnderwritingProofBook()

# Initialize crawlers
crawlers = {
    "code": CodeCrawler(),
    "dependency": DependencyCrawler(),
    "license": LicenseCrawler(),
    "security": SecurityCrawler(),
    "test_build": TestBuildCrawler(),
    "browser_runtime": BrowserRuntimeCrawler()
}

# Initialize underwriting clients (with None API keys - user must provide)
fema_client = FEMAClient()
sanctions_engine = None  # Requires OFACClient initialization

# Storage paths
STORAGE_PATH = Path("storage")
STORAGE_PATH.mkdir(exist_ok=True)
TEMP_PATH = Path("temp")
TEMP_PATH.mkdir(exist_ok=True)


# Request/Response Models
class CrawlRequest(BaseModel):
    source_url: str
    source_type: str = "repo"
    crawler_types: List[str] = ["code"]
    priority: int = 0


class CrawlResponse(BaseModel):
    success: bool
    source_id: str
    results: Dict[str, Any]
    receipt_id: Optional[str] = None


class UnderwritingRequest(BaseModel):
    source_url: str
    source_type: str = "repo"
    include_proofbook: bool = True


class ScoreRequest(BaseModel):
    source_id: str


class ReceiptRequest(BaseModel):
    receipt_id: str


class SanctionsCheckRequest(BaseModel):
    name: str
    address: Optional[str] = None


class FEMARiskRequest(BaseModel):
    county_fips: Optional[str] = None
    state_fips: Optional[str] = None
    tract_id: Optional[str] = None


class AddressValidationRequest(BaseModel):
    street: str
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None


# Health Check
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Layer Crawler ETL Engine",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "crawl": "/crawl",
            "underwrite": "/underwrite",
            "score": "/score",
            "receipts": "/receipts",
            "sanctions": "/sanctions/check",
            "fema": "/fema/risk",
            "address": "/address/validate"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "components": {
            "source_registry": "ok",
            "job_queue": "ok",
            "receipt_ledger": "ok",
            "proofbook": "ok"
        }
    }


# Source Registration
@app.post("/sources/register")
async def register_source(
    source_url: str,
    source_type: str = "repo",
    name: Optional[str] = None,
    priority: int = 0
):
    """Register a new source for crawling."""
    from layer_crawler_etl.layer0_source_registry.source_registry import SourceType
    
    source_type_enum = SourceType(source_type)
    
    if not name:
        name = source_url.rstrip("/").split("/")[-1]
    
    source = source_registry.register_source(
        source_type_enum,
        source_url,
        name,
        priority=priority
    )
    
    return {
        "success": True,
        "source_id": source.source_id,
        "source": source.to_dict()
    }


@app.get("/sources")
async def list_sources():
    """List all registered sources."""
    return {
        "sources": [s.to_dict() for s in source_registry.sources.values()],
        "stats": source_registry.get_stats()
    }


@app.get("/sources/{source_id}")
async def get_source(source_id: str):
    """Get a specific source."""
    source = source_registry.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source.to_dict()


# Crawling Endpoints
@app.post("/crawl")
async def crawl_source(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Crawl a source with specified crawler types.
    Returns results and generates a receipt.
    """
    # Register source if not exists
    from layer_crawler_etl.layer0_source_registry.source_registry import SourceType
    
    source_type_enum = SourceType(request.source_type)
    source = source_registry.register_source(
        source_type_enum,
        request.source_url,
        request.source_url.rstrip("/").split("/")[-1],
        priority=request.priority
    )
    
    # Run crawlers
    results = {}
    all_signals = {}
    all_scores = {}
    
    for crawler_type in request.crawler_types:
        if crawler_type not in crawlers:
            results[crawler_type] = {"error": f"Crawler type {crawler_type} not available"}
            continue
        
        crawler = crawlers[crawler_type]
        try:
            crawl_result = await crawler.crawl(source)
            results[crawler_type] = crawl_result.to_dict()
            
            # ETL pipeline
            if crawl_result.success:
                extracted = Extractor().extract_from_crawl_result(crawl_result)
                normalized = Transformer().transform(extracted)
                Loader().load(normalized)
                
                # Score
                score_result = Scorer().score(normalized)
                all_signals.update(normalized.signals)
                all_scores[crawler_type] = score_result.to_dict()
                
                # Generate actions
                actions = ActionEngine().generate_actions(score_result, normalized.data)
                results[crawler_type]["actions"] = actions.to_dict()
            
        except Exception as e:
            results[crawler_type] = {"error": str(e)}
    
    # Generate receipt
    receipt = receipt_generator.generate_crawler_receipt(
        source_id=source.source_id,
        crawler_type=request.crawler_types[0] if request.crawler_types else "multi",
        crawl_result=results,
        score_result=all_scores
    )
    receipt_ledger.add_receipt(receipt)
    
    # Add to ProofBook
    try:
        chain_id = proofbook.create_underwriting_chain(source.source_id)
        proofbook.submit_crawler_evidence(source.source_id, results, chain_id)
    except Exception as e:
        pass  # ProofBook is optional
    
    return CrawlResponse(
        success=True,
        source_id=source.source_id,
        results=results,
        receipt_id=receipt.receipt_id
    )


@app.post("/crawl/submit")
async def submit_crawl_job(
    source_url: str,
    crawler_type: str = "code",
    priority: int = 0
):
    """Submit a crawl job to the queue (async)."""
    from layer_crawler_etl.layer0_source_registry.source_registry import SourceType
    
    source_type_enum = SourceType("repo")
    source = source_registry.register_source(
        source_type_enum,
        source_url,
        source_url.rstrip("/").split("/")[-1],
        priority=priority
    )
    
    job = await job_queue.submit_job(
        source_id=source.source_id,
        crawler_type=crawler_type,
        priority=priority
    )
    
    return {
        "success": True,
        "job_id": job.job_id,
        "source_id": source.source_id,
        "status": job.status.value
    }


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a crawl job."""
    job = await job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@app.get("/jobs/stats")
async def get_job_stats():
    """Get job queue statistics."""
    return job_queue.get_stats()


# Scoring Endpoints
@app.post("/score")
async def score_source(request: ScoreRequest):
    """Score a source based on previous crawl results."""
    from layer_crawler_etl.layer2_etl import Loader
    
    loader = Loader()
    records = loader.load_by_source_id(request.source_id)
    
    if not records:
        raise HTTPException(status_code=404, detail="No crawl results found for source")
    
    scorer = Scorer()
    scores = []
    
    for record_data in records:
        from layer_crawler_etl.layer2_etl.transformer import NormalizedRecord
        record = NormalizedRecord(
            source_id=record_data["source_id"],
            record_type=record_data["record_type"],
            data=record_data["data"],
            signals=record_data["signals"],
            timestamp=record_data["timestamp"],
            hash=record_data["hash"]
        )
        score_result = scorer.score(record)
        scores.append(score_result.to_dict())
    
    return {
        "source_id": request.source_id,
        "scores": scores,
        "count": len(scores)
    }


# Underwriting Endpoints
@app.post("/underwrite")
async def underwrite_source(request: UnderwritingRequest):
    """
    Full underwriting pipeline for a source.
    Includes crawling, scoring, and decision generation.
    """
    from layer_crawler_etl.layer0_source_registry.source_registry import SourceType
    
    source_type_enum = SourceType(request.source_type)
    source = source_registry.register_source(
        source_type_enum,
        request.source_url,
        request.source_url.rstrip("/").split("/")[-1]
    )
    
    # Run all crawlers
    crawler_types = ["code", "dependency", "license", "security", "test_build"]
    crawl_request = CrawlRequest(
        source_url=request.source_url,
        source_type=request.source_type,
        crawler_types=crawler_types
    )
    
    crawl_result = await crawl_source(crawl_request, BackgroundTasks())
    
    # Generate underwriting decision
    decision = _generate_underwriting_decision(crawl_result)
    
    # Add to ProofBook if requested
    chain_id = None
    if request.include_proofbook:
        chain_id = proofbook.create_underwriting_chain(source.source_id)
        proofbook.submit_underwriting_memo(source.source_id, decision, chain_id)
    
    return {
        "source_id": source.source_id,
        "decision": decision,
        "crawl_result": crawl_result,
        "proofbook_chain_id": chain_id
    }


def _generate_underwriting_decision(crawl_result: CrawlResponse) -> Dict:
        """Generate underwriting decision from crawl results."""
        results = crawl_result.results
        
        # Extract signals
        secrets_exposed = sum(
            r.get("data", {}).get("secrets_found", 0)
            for r in results.values() if isinstance(r, dict)
        )
        
        license_conflicts = sum(
            len(r.get("data", {}).get("conflicts", []))
            for r in results.values() if isinstance(r, dict)
        )
        
        # Determine risk grade
        if secrets_exposed > 0 or license_conflicts > 0:
            risk_grade = "E"
            borrowing_base = 0
        else:
            risk_grade = "C"
            borrowing_base = 41645  # Example value
        
        return {
            "risk_grade": risk_grade,
            "borrowing_base": borrowing_base,
            "conditions": [
                "No secrets exposed",
                "No license conflicts",
                "Tests present"
            ],
            "covenants": [
                "Maintain test coverage",
                "Regular security scans"
            ],
            "memo": f"Source {crawl_result.source_id} assessed with risk grade {risk_grade}"
        }


# Receipts Endpoints
@app.get("/receipts/{receipt_id}")
async def get_receipt(receipt_id: str):
    """Get a receipt by ID."""
    receipt = receipt_ledger.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt.to_dict()


@app.get("/receipts/source/{source_id}")
async def get_receipts_by_source(source_id: str):
    """Get all receipts for a source."""
    receipts = receipt_ledger.get_receipts_by_source(source_id)
    return {
        "source_id": source_id,
        "receipts": [r.to_dict() for r in receipts],
        "count": len(receipts)
    }


@app.post("/receipts/{receipt_id}/verify")
async def verify_receipt(receipt_id: str):
    """Verify a receipt's integrity."""
    receipt = receipt_ledger.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    is_valid = receipt_verifier.verify_receipt(receipt)
    report = receipt_verifier.generate_verification_report(receipt)
    
    return {
        "receipt_id": receipt_id,
        "valid": is_valid,
        "report": report
    }


@app.get("/receipts/stats")
async def get_receipt_stats():
    """Get receipt ledger statistics."""
    return receipt_ledger.get_stats()


# Sanctions Screening Endpoints
@app.post("/sanctions/check")
async def check_sanctions(request: SanctionsCheckRequest):
    """Check if a name is on sanctions lists."""
    ofac_client = OFACClient()
    sanctions_engine = SanctionsComplianceEngine(ofac_client)
    
    result = await sanctions_engine.screen_individual(
        name=request.name,
        address=request.address
    )
    
    return result


# FEMA Risk Endpoints
@app.post("/fema/risk")
async def get_fema_risk(request: FEMARiskRequest):
    """Get FEMA National Risk Index data."""
    response = await fema_client.get_national_risk_index(
        county_fips=request.county_fips,
        state_fips=request.state_fips,
        tract_id=request.tract_id
    )
    
    if response.success:
        risk_data = fema_client.parse_risk_score(response)
        return risk_data
    else:
        raise HTTPException(status_code=400, detail=response.errors)


# Address Validation Endpoints
@app.post("/address/validate")
async def validate_address(request: AddressValidationRequest):
    """Validate and standardize an address."""
    # This requires Smarty credentials
    return {
        "success": False,
        "error": "Address validation requires Smarty credentials. Configure SMARTY_AUTH_ID and SMARTY_AUTH_TOKEN environment variables."
    }


# OCR Endpoints
@app.post("/ocr/extract")
async def extract_text_from_image(file: UploadFile = File(...)):
    """Extract text from an uploaded image using OCR."""
    # Save uploaded file
    temp_file = TEMP_PATH / file.filename
    with open(temp_file, "wb") as f:
        f.write(await file.read())
    
    # Extract text
    ocr_processor = OCRProcessor()
    result = await ocr_processor.extract_text_from_image(str(temp_file))
    
    # Clean up
    temp_file.unlink()
    
    return result


# ProofBook Endpoints
@app.get("/proofbook/stats")
async def get_proofbook_stats():
    """Get ProofBook statistics."""
    return proofbook.get_stats()


@app.get("/proofbook/chain/{chain_id}")
async def get_proofbook_chain(chain_id: str):
    """Get a ProofBook chain."""
    chain = proofbook.get_chain(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    return chain.to_dict()


@app.post("/proofbook/chain/{chain_id}/verify")
async def verify_proofbook_chain(chain_id: str):
    """Verify a ProofBook chain's integrity."""
    is_valid = proofbook.verify_chain(chain_id)
    
    return {
        "chain_id": chain_id,
        "valid": is_valid
    }


# Stats Endpoints
@app.get("/stats")
async def get_system_stats():
    """Get system-wide statistics."""
    return {
        "sources": source_registry.get_stats(),
        "jobs": job_queue.get_stats(),
        "receipts": receipt_ledger.get_stats(),
        "proofbook": proofbook.get_stats()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
