import importlib
import re

import gradio as gr
import yaml
# from gradio.inputs import Textbox

from inference.base_tts_infer import BaseTTSInfer
from utils.hparams import set_hparams
from utils.hparams import hparams as hp
import numpy as np

from data_gen.tts.data_gen_utils import is_sil_phoneme, PUNCS

class GradioInfer:
    def __init__(self, exp_name, config, inference_cls, title, description, article, example_inputs):
        self.exp_name = exp_name
        self.config = config
        self.title = title
        self.description = description
        self.article = article
        self.example_inputs = example_inputs
        pkg = ".".join(inference_cls.split(".")[:-1])
        cls_name = inference_cls.split(".")[-1]
        self.inference_cls = getattr(importlib.import_module(pkg), cls_name)

    def greet(self, text, pitch_shift, speaker_id):
        sents = re.split(rf'([{PUNCS}])', text.replace('\n', ','))
        if sents[-1] not in list(PUNCS):
            sents = sents + ['.']
        audio_outs = []
        s = ""
        for i in range(0, len(sents), 2):
            if len(sents[i]) > 0:
                s += sents[i] + sents[i + 1]
            if len(s) >= 400 or (i >= len(sents) - 2 and len(s) > 0):
                # Convert speaker_id string to index 
                # If spk_map: {"spk0": 0, "spk1": 1}
                if isinstance(speaker_id, str):
                    speaker_id = self.infer_ins.spk_map[speaker_id]

                # Perform inference
                audio_out = self.infer_ins.infer_once({
                    'text': s,
                    'pitch_shift_smitones': pitch_shift,
                    'speaker_id': speaker_id
                })
                audio_out = audio_out * 32767
                audio_out = audio_out.astype(np.int16)
                audio_outs.append(audio_out)
                audio_outs.append(np.zeros(int(hp['audio_sample_rate'] * 0.3)).astype(np.int16))
                s = ""
        audio_outs = np.concatenate(audio_outs)
        return hp['audio_sample_rate'], audio_outs

    def run(self):
        set_hparams(exp_name=self.exp_name, config=self.config)
        infer_cls = self.inference_cls
        self.infer_ins: BaseTTSInfer = infer_cls(hp)
        example_inputs = self.example_inputs
        iface = gr.Interface(fn=self.greet,
                             inputs=[
                                 gr.Textbox(lines=10, placeholder="", value=example_inputs[0][0], label="Input Text"),
                                 gr.Slider(minimum=-120, maximum=120, step=1, value=0, label="Pitch Shift (semitones)"),
                                 gr.Dropdown(choices=list(self.infer_ins.spk_map.keys()), label="Speaker Id")
                             ],
                             outputs="audio",
                             allow_flagging="never",
                             title=self.title,
                             description=self.description,
                             article=self.article,
                             examples=example_inputs)
        iface.launch(share=True)


if __name__ == '__main__':
    gradio_config = yaml.safe_load(open('inference/gradio/gradio_settings.yaml'))
    g = GradioInfer(**gradio_config)
    g.run()
