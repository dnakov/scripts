from mlx_lm import load, generate

model, tokenizer = load("mlx-community/QwQ-32B-Preview-8bit")

from prompts import prompts

messages = prompts['messages']
tools = prompts['tools']

if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template is not None:
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, 
        tools=tools
    )

response = generate(model, tokenizer, prompt=prompt, verbose=True)
