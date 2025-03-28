import asyncio
from services.llm_processor import process_input_async
from models.dataclasses import ChatState

def process_input(state: ChatState, user_input: str) -> str:
    return asyncio.run(process_input_async(state, user_input))

#DEBUGGING ONLY
def main():
    print("Flight Status[DEBUGGING]")
    print("=====================")
    state = ChatState()
    initial_response = "Hey there! How can I help you with flight status today?"
    print(f"BOT: {initial_response}")
    state.add_message("assistant", initial_response)
    
    while True:
        user_input = input("YOU: ")
        if user_input.lower() == "exit":
            print("BOT: See you next time! Safe travels!")
            break
        
        response = process_input(state, user_input)
        print(f"---\nBOT: {response}\n---")
        state.add_message("user", user_input)
        state.add_message("assistant", response)

if __name__ == "__main__":
    main()