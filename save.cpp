#include <fstream>
#include <string>
#include <iostream>

#define size 10
using namespace std; 

int main(){

        signal(SIGINT, sigint);
        fstream file; 
        
        for(int i = 1000;  i<=47000; i+=1000){

            file.open("./log/20210110_190115_BreakoutNoFrameskip-v4/weights/checkpoint", ios::out | ios::trunc);

            file << "model_checkpoint_path: \"episode_";
            file << i;
            file << "\" \n";
            file << "all_model_checkpoint_paths: \"episode_";
            file << i;
            file << "\"";
            file.close(); 

            string cmd = ("python main.py --env BreakoutNoFrameskip-v4 --save " + to_string(i));

            int a = system(cmd.c_str());

            cout << i << endl;

        }
            
    return 0;
}