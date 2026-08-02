// ================= COMMUNITY =================

const feedContainer = document.getElementById("feed-container");
const postBtn = document.getElementById("create-post-btn");

// Load posts when page opens
window.addEventListener("DOMContentLoaded", loadPosts);

// ---------------- LOAD POSTS ----------------

async function loadPosts() {

    try {

        const res = await fetch("/posts");
        const posts = await res.json();

        feedContainer.innerHTML = "";

        posts.forEach(post=>{

            feedContainer.innerHTML += `

            <div class="glass-card community-post">

                <div class="post-header">

                    <div class="post-avatar">🌾</div>

                    <div class="post-user">

                        <div class="post-name">
                            ${post.name}
                        </div>

                        <div class="post-time">
                            ${post.created_at}
                        </div>

                    </div>

                </div>

                <div class="post-content">
                    ${post.text}
                </div>

                ${
                    post.image
                    ?
                    `<img class="post-image" src="${post.image}">`
                    :
                    ""
                }

            </div>

            `;

        });

    }

    catch(err){

        console.log(err);

    }

}

// ---------------- CREATE POST ----------------

postBtn.addEventListener("click", createPost);

async function createPost(){

    const name = document.getElementById("post-name").value.trim();
    const text = document.getElementById("post-text").value.trim();
    const imageInput = document.getElementById("post-image");

    if(name==="" || text===""){

        alert("Please enter your name and post.");

        return;

    }

    let image = "";

    if(imageInput.files.length>0){

        const file = imageInput.files[0];

        image = await toBase64(file);

    }

    const res = await fetch("/posts",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({

            name:name,
            text:text,
            image:image

        })

    });

    const data = await res.json();

    if(data.success){

        document.getElementById("post-name").value="";
        document.getElementById("post-text").value="";
        document.getElementById("post-image").value="";

        loadPosts();

    }

    else{

        alert("Unable to post.");

    }

}

// ---------------- IMAGE TO BASE64 ----------------

function toBase64(file){

    return new Promise((resolve,reject)=>{

        const reader = new FileReader();

        reader.readAsDataURL(file);

        reader.onload=()=>resolve(reader.result);

        reader.onerror=error=>reject(error);

    });

}