function confirmation(name) {
    var result = confirm("Sei sicuro di voler eliminare " + name + " ?");
    if (result) {
        document.getElementById(name).value = name;
        return true;
    } else {
        document.getElementById("confirmed").value = "False";
        return false;
    }
}

function usersubmit() {
    alert("Utente creato!")
}

function passwordsubmit(){
    alert("Password generata! Controllare la mail associata.")
}