import { FaGithub, FaLinkedin, FaTwitter } from "react-icons/fa";

const DeveloperCard = ({ developer }) => {
  return (
    <div className="bg-white rounded-2xl shadow-lg p-5 text-center w-80">
      <img
        src={developer.image}
        alt={developer.name}
        className="w-24 h-24 rounded-full mx-auto mb-4 border-4 border-gray-200"
      />
      <h2 className="text-xl font-semibold">{developer.name}</h2>
      <p className="text-gray-600">{developer.role}</p>
      <div className="flex justify-center gap-4 mt-3">
        {developer.github && (
          <a
            href={developer.github}
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-700 hover:text-black text-2xl"
          >
            <FaGithub />
          </a>
        )}
        {developer.linkedin && (
          <a
            href={developer.linkedin}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-700 hover:text-blue-900 text-2xl"
          >
            <FaLinkedin />
          </a>
        )}
        {developer.twitter && (
          <a
            href={developer.twitter}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-600 text-2xl"
          >
            <FaTwitter />
          </a>
        )}
      </div>
    </div>
  );
};

const DeveloperList = () => {
  const developers = [
    {
      name: "Aashish Shrestha",
      role: "Development Operations",
      image: "/assets/aashish.jpg",
      github: "https://github.com/johndoe",
      linkedin: "https://linkedin.com/in/johndoe",
      twitter: "https://twitter.com/johndoe",
    },
    {
      name: "Divya Shangkat Karki",
      role: "FullStack Developer",
      image: "/assets/divya.jpg",
      github: "https://github.com/janesmith",
      linkedin: "https://linkedin.com/in/janesmith",
      twitter: "https://twitter.com/janesmith",
    },
    {
      name: "Khagendra Karki",
      role: "Machine learning engineer",
      image: "/assets/khagendra.jpg",
      github: "https://github.com/janesmith",
      linkedin: "https://linkedin.com/in/janesmith",
      twitter: "https://twitter.com/janesmith",
    },
  ];

  return (
    <div className="flex flex-wrap justify-center gap-6 p-10">
      {developers.map((dev, index) => (
        <DeveloperCard key={index} developer={dev} />
      ))}
    </div>
  );
};

export default DeveloperList;
