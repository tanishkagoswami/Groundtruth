"""Generates golden_set.jsonl. Labels are TENTATIVE (verified=false) -> check each against the paper.
gpu: list of keywords that must appear in extracted compute (lowercased substring match)
     [] + gpu_mentioned=False  -> paper states no hardware; tool must NOT invent any (hallucination test)
     None                      -> I'm unsure; case is skipped for GPU grading until you label it
tier: 'extreme' => score must be low; None => no score-range check
"""
import json
A = "https://arxiv.org/abs/"
G = "https://github.com/"
# (id, category, arxiv, repo, gpu_keywords, gpu_mentioned, tier)
C = [
 ("big_01","big_compute",A+"2302.13971",G+"facebookresearch/llama",["a100"],True,"extreme"),
 ("big_02","big_compute",A+"2204.02311",None,["tpu"],True,"extreme"),
 ("big_03","big_compute",A+"2307.09288",G+"meta-llama/llama",["a100"],True,"extreme"),
 ("big_04","big_compute",A+"2203.15556",None,["tpu"],True,"extreme"),
 ("big_05","big_compute",A+"2005.14165",None,["v100"],True,"extreme"),
 ("tpu_01","tpu_based",A+"1810.04805",G+"google-research/bert",["tpu"],True,None),
 ("tpu_02","tpu_based",A+"2010.11929",G+"google-research/vision_transformer",["tpu"],True,None),
 ("tpu_03","tpu_based",A+"1910.10683",G+"google-research/text-to-text-transfer-transformer",["tpu"],True,None),
 ("tpu_04","tpu_based",A+"2006.11239",G+"hojonathanho/diffusion",["tpu"],True,None),
 ("gpu_01","gpu_known",A+"1706.03762",G+"tensorflow/tensor2tensor",["p100"],True,None),
 ("gpu_02","gpu_known",A+"1409.1556",None,["titan"],True,None),
 ("gpu_03","gpu_known",A+"1506.01497",G+"rbgirshick/py-faster-rcnn",["k40"],True,None),
 ("gpu_04","gpu_known",A+"1506.02640",G+"pjreddie/darknet",["titan"],True,None),
 ("gpu_05","gpu_known",A+"2005.12872",G+"facebookresearch/detr",["v100"],True,None),
 ("gpu_06","gpu_known",A+"2205.14135",G+"Dao-AILab/flash-attention",["a100"],True,None),
 ("gpu_07","gpu_known",A+"2307.08691",G+"Dao-AILab/flash-attention",["a100"],True,None),
 ("gpu_08","gpu_known",A+"2309.06180",G+"vllm-project/vllm",["a100"],True,None),
 ("gpu_09","gpu_known",A+"2312.00752",G+"state-spaces/mamba",["a100"],True,None),
 ("gpu_10","gpu_known",A+"2304.02643",G+"facebookresearch/segment-anything",["a100"],True,None),
 ("gpu_11","gpu_known",A+"2112.10752",G+"CompVis/latent-diffusion",["a100"],True,None),
 ("gpu_12","gpu_known",A+"2305.14314",G+"artidoro/qlora",["gpu"],True,None),
 ("gpu_13","gpu_known",A+"2103.00020",G+"openai/CLIP",["v100"],True,None),
 ("gpu_14","gpu_known",A+"1907.11692",G+"facebookresearch/fairseq",["v100"],True,None),
 ("none_01","no_hardware",A+"1412.6980",None,[],False,None),
 ("none_02","no_hardware",A+"1301.3781",None,[],False,None),
 ("none_03","no_hardware",A+"1503.02531",None,[],False,None),
 ("none_04","no_hardware",A+"1406.2661",G+"goodfeli/adversarial",[],False,None),
 ("none_05","no_hardware",A+"2201.11903",None,[],False,None),
 ("none_06","no_hardware",A+"2210.03629",G+"ysymyth/ReAct",[],False,None),
 ("none_07","no_hardware",A+"2305.10601",G+"princeton-nlp/tree-of-thought-llm",[],False,None),
 ("none_08","no_hardware",A+"2212.08073",None,[],False,None),
 ("none_09","no_hardware",A+"2303.08774",None,[],False,None),
 ("unk_01","needs_labeling",A+"1512.03385",None,None,None,None),
 ("unk_02","needs_labeling",A+"2106.09685",G+"microsoft/LoRA",None,None,None),
 ("unk_03","needs_labeling",A+"2212.04356",G+"openai/whisper",None,None,None),
 ("unk_04","needs_labeling",A+"2010.02502",None,None,None,None),
 ("unk_05","needs_labeling",A+"2310.06825",G+"mistralai/mistral-inference",None,None,None),
 ("unk_06","needs_labeling",A+"2401.04088",None,None,None,None),
 ("unk_07","needs_labeling",A+"2106.07447",G+"facebookresearch/fairseq",None,None,None),
 ("unk_08","needs_labeling",A+"2201.12086",None,None,None,None),
 ("unk_09","needs_labeling",A+"1312.5602",None,None,None,None),
 ("unk_10","needs_labeling",A+"1707.06347",None,None,None,None),
 ("unk_11","needs_labeling",A+"1711.05101",None,None,None,None),
 ("unk_12","needs_labeling",A+"2001.08361",None,None,None,None),
]
EDGE = [  # expect graceful error (4xx or {"error":...}), never a 500/crash/hang
 ("edge_01","edge_input","not a url",None),
 ("edge_02","edge_input",A+"9999.99999",None),
 ("edge_03","edge_input","https://example.com/paper.pdf",None),
 ("edge_04","edge_input",A+"1706.03762",G+"this-does-not/exist-xyz-404"),
]
OK = [  # valid inputs in unusual shapes; must succeed
 ("edge_05","edge_input_ok","https://arxiv.org/pdf/1706.03762",None),
 ("edge_06","edge_input_ok",A+"hep-th/9711200",None),  # old-style ID, pure theory paper
]
with open("golden_set.jsonl","w") as f:
    for id_,cat,ax,repo,gpu,gm,tier in C:
        f.write(json.dumps(dict(id=id_,category=cat,arxiv_url=ax,github_url=repo,
            gpu_keywords=gpu,gpu_mentioned=gm,tier=tier,expect_error=False,verified=False))+"\n")
    for id_,cat,ax,repo in EDGE:
        f.write(json.dumps(dict(id=id_,category=cat,arxiv_url=ax,github_url=repo,expect_error=True,verified=True))+"\n")
    for id_,cat,ax,repo in OK:
        f.write(json.dumps(dict(id=id_,category=cat,arxiv_url=ax,github_url=repo,gpu_keywords=None,gpu_mentioned=None,
            tier=None,expect_error=False,verified=False))+"\n")
print("wrote golden_set.jsonl")